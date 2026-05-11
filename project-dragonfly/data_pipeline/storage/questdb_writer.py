"""QuestDB writer for real-time OHLCV and orderbook data."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class OHLCVRecord:
    """OHLCV record for QuestDB insertion."""
    exchange: str
    symbol: str
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str


class QuestDBWriter:
    """
    Writes real-time market data to QuestDB via HTTP REST API.

    Supports batch inserts for efficiency.
    Auto-creates tables if they don't exist.
    """

    TABLE_OHLCV_1M = "ohlcv_1m"
    TABLE_OHLCV_5M = "ohlcv_5m"
    TABLE_OHLCV_1H = "ohlcv_1h"
    TABLE_ORDERBOOK = "orderbook_snapshots"
    TABLE_TRADES = "trades"

    def __init__(self, host: str = "localhost", port: int = 9000, batch_size: int = 100, flush_interval_ms: int = 1000):
        """
        Initialize QuestDBWriter.

        Args:
            host: QuestDB host
            port: QuestDB HTTP port
            batch_size: Max rows per batch insert
            flush_interval_ms: Flush interval in milliseconds
        """
        self.host = host
        self.port = port
        self.batch_size = batch_size
        self.flush_interval_ms = flush_interval_ms
        self.base_url = f"http://{host}:{port}"

        self._ohlcv_buffer: List[str] = []
        self._orderbook_buffer: List[str] = []
        self._trades_buffer: List[str] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the writer and ensure tables exist."""
        self._running = True
        await self._ensure_tables()
        self._flush_task = asyncio.create_task(self._flush_loop())

    async def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        tables = [
            (
                self.TABLE_OHLCV_1M,
                "CREATE TABLE IF NOT EXISTS ohlcv_1m ("
                "exchange STRING, symbol SYMBOL, timestamp TIMESTAMP, "
                "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE, "
                "timeframe STRING, closed BOOLEAN) "
                "timestamp(timestamp) PARTITION BY DAY;"
            ),
            (
                self.TABLE_OHLCV_5M,
                "CREATE TABLE IF NOT EXISTS ohlcv_5m ("
                "exchange STRING, symbol SYMBOL, timestamp TIMESTAMP, "
                "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE, "
                "timeframe STRING, closed BOOLEAN) "
                "timestamp(timestamp) PARTITION BY DAY;"
            ),
            (
                self.TABLE_OHLCV_1H,
                "CREATE TABLE IF NOT EXISTS ohlcv_1h ("
                "exchange STRING, symbol SYMBOL, timestamp TIMESTAMP, "
                "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE, "
                "timeframe STRING, closed BOOLEAN) "
                "timestamp(timestamp) PARTITION BY DAY;"
            ),
            (
                self.TABLE_ORDERBOOK,
                "CREATE TABLE IF NOT EXISTS orderbook_snapshots ("
                "exchange STRING, symbol SYMBOL, timestamp TIMESTAMP, "
                "bids STRING, asks STRING, depth INT) "
                "timestamp(timestamp) PARTITION BY DAY;"
            ),
            (
                self.TABLE_TRADES,
                "CREATE TABLE IF NOT EXISTS trades ("
                "exchange STRING, symbol SYMBOL, timestamp TIMESTAMP, "
                "price DOUBLE, size DOUBLE, side STRING, trade_id STRING) "
                "timestamp(timestamp) PARTITION BY DAY;"
            ),
        ]

        async with aiohttp.ClientSession() as session:
            for name, create_sql in tables:
                try:
                    async with session.post(
                        f"{self.base_url}/exec",
                        data=create_sql.encode(),
                        headers={"Content-Type": "text/plain"},
                    ) as resp:
                        if resp.status not in (200, 201, 204):
                            text = await resp.text()
                            logger.warning("Table %s creation response: %s", name, text)
                        else:
                            logger.info("Table %s ensured", name)
                except Exception as e:
                    logger.error("Failed to create table %s: %s", name, e)

    async def write_ohlcv(self, ohlcv: Dict[str, Any]) -> None:
        """
        Buffer an OHLCV record for batch insert.

        Args:
            ohlcv: OHLCV dict from queue
        """
        exchange = ohlcv.get("exchange", "")
        symbol = ohlcv.get("symbol", "")
        timestamp = ohlcv.get("timestamp", 0)
        open_ = ohlcv.get("open", 0)
        high = ohlcv.get("high", 0)
        low = ohlcv.get("low", 0)
        close = ohlcv.get("close", 0)
        volume = ohlcv.get("volume", 0)
        timeframe = ohlcv.get("timeframe", "1m")
        closed = ohlcv.get("closed", True)

        # Select table by timeframe
        table_map = {"1m": self.TABLE_OHLCV_1M, "5m": self.TABLE_OHLCV_5M, "1h": self.TABLE_OHLCV_1H}
        table = table_map.get(timeframe, self.TABLE_OHLCV_1M)

        row = f"'{exchange}','{symbol}',{timestamp},{open_},{high},{low},{close},{volume},'{timeframe}',{closed}"
        async with self._buffer_lock:
            self._ohlcv_buffer.append(row)
            if len(self._ohlcv_buffer) >= self.batch_size:
                await self._flush_ohlcv()

    async def write_orderbook(self, symbol: str, bids: List, asks: List) -> None:
        """
        Buffer an orderbook snapshot for batch insert.

        Args:
            symbol: Trading pair
            bids: List of [price, size] pairs
            asks: List of [price, size] pairs
        """
        import json
        timestamp = int(asyncio.get_event_loop().time() * 1000)
        bids_json = json.dumps(bids)
        asks_json = json.dumps(asks)

        row = f"'internal','{symbol}',{timestamp},'{bids_json}','{asks_json}',{len(bids)}"
        async with self._buffer_lock:
            self._orderbook_buffer.append(row)
            if len(self._orderbook_buffer) >= self.batch_size:
                await self._flush_orderbook()

    async def write_trade(self, trade: Dict[str, Any]) -> None:
        """Buffer a trade record for batch insert."""
        exchange = trade.get("exchange", "")
        symbol = trade.get("symbol", "")
        timestamp = trade.get("timestamp", 0)
        price = trade.get("price", 0)
        size = trade.get("size", 0)
        side = trade.get("side", "unknown")
        trade_id = trade.get("trade_id", "")

        row = f"'{exchange}','{symbol}',{timestamp},{price},{size},'{side}','{trade_id}'"
        async with self._buffer_lock:
            self._trades_buffer.append(row)
            if len(self._trades_buffer) >= self.batch_size:
                await self._flush_trades()

    async def _flush_ohlcv(self) -> None:
        """Flush buffered OHLCV records to QuestDB."""
        if not self._ohlcv_buffer:
            return

        rows = ";\n".join(self._ohlcv_buffer) + ";"
        self._ohlcv_buffer.clear()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/exec",
                    data=f"INSERT INTO {self.TABLE_OHLCV_1M} VALUES {rows}".encode(),
                    headers={"Content-Type": "text/plain"},
                ) as resp:
                    if resp.status not in (200, 201, 204):
                        logger.error("OHLCV flush error: %s", await resp.text())
        except Exception as e:
            logger.error("OHLCV flush exception: %s", e)

    async def _flush_orderbook(self) -> None:
        """Flush buffered orderbook records to QuestDB."""
        if not self._orderbook_buffer:
            return

        rows = ";\n".join(self._orderbook_buffer) + ";"
        self._orderbook_buffer.clear()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/exec",
                    data=f"INSERT INTO {self.TABLE_ORDERBOOK} VALUES {rows}".encode(),
                    headers={"Content-Type": "text/plain"},
                ) as resp:
                    if resp.status not in (200, 201, 204):
                        logger.error("Orderbook flush error: %s", await resp.text())
        except Exception as e:
            logger.error("Orderbook flush exception: %s", e)

    async def _flush_trades(self) -> None:
        """Flush buffered trade records to QuestDB."""
        if not self._trades_buffer:
            return

        rows = ";\n".join(self._trades_buffer) + ";"
        self._trades_buffer.clear()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/exec",
                    data=f"INSERT INTO {self.TABLE_TRADES} VALUES {rows}".encode(),
                    headers={"Content-Type": "text/plain"},
                ) as resp:
                    if resp.status not in (200, 201, 204):
                        logger.error("Trades flush error: %s", await resp.text())
        except Exception as e:
            logger.error("Trades flush exception: %s", e)

    async def _flush_loop(self) -> None:
        """Periodic flush loop."""
        while self._running:
            await asyncio.sleep(self.flush_interval_ms / 1000)
            async with self._buffer_lock:
                await self._flush_ohlcv()
                await self._flush_orderbook()
                await self._flush_trades()

    async def flush(self) -> None:
        """Manually flush all buffers."""
        async with self._buffer_lock:
            await self._flush_ohlcv()
            await self._flush_orderbook()
            await self._flush_trades()

    async def stop(self) -> None:
        """Stop the writer and flush remaining data."""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
        await self.flush()
        logger.info("QuestDBWriter stopped")
