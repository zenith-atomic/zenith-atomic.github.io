"""ClickHouse writer for warm analytics data."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ClickHouseWriter:
    """
    Writes market data to ClickHouse for warm analytics.

    Used for analytical queries with a 30-day window.
    """

    TABLE_OHLCV = "ohlcv"
    TABLE_ORDERBOOK = "orderbook_snapshots"
    TABLE_TRADES = "trades"

    def __init__(self, host: str = "localhost", port: int = 9000, database: str = "dragonfly"):
        """
        Initialize ClickHouseWriter.

        Args:
            host: ClickHouse host
            port: ClickHouse port
            database: Database name
        """
        self.host = host
        self.port = port
        self.database = database
        self._client = None
        self._buffer: List[Dict[str, Any]] = []
        self._buffer_lock = asyncio.Lock()
        self._running = False

    async def connect(self) -> bool:
        """Connect to ClickHouse."""
        try:
            from clickhouse_driver import Client
            self._client = Client(
                host=self.host,
                port=self.port,
                database=self.database,
                connect_timeout=5,
            )
            logger.info("Connected to ClickHouse at %s:%s", self.host, self.port)
            return True
        except Exception as e:
            logger.error("ClickHouse connection failed: %s", e)
            return False

    async def start(self) -> None:
        """Start the writer and ensure tables exist."""
        self._running = True
        await self._ensure_tables()

    async def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        create_sqls = [
            f"CREATE DATABASE IF NOT EXISTS {self.database}",
            f"""
            CREATE TABLE IF NOT EXISTS {self.database}.{self.TABLE_OHLCV} (
                exchange String,
                symbol String,
                timestamp DateTime64(3),
                open Float64,
                high Float64,
                low Float64,
                close Float64,
                volume Float64,
                timeframe String,
                closed UInt8
            ) ENGINE = MergeTree()
            ORDER BY (exchange, symbol, timestamp)
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self.database}.{self.TABLE_ORDERBOOK} (
                exchange String,
                symbol String,
                timestamp DateTime64(3),
                bids String,
                asks String,
                depth UInt16
            ) ENGINE = MergeTree()
            ORDER BY (exchange, symbol, timestamp)
            """,
            f"""
            CREATE TABLE IF NOT EXISTS {self.database}.{self.TABLE_TRADES} (
                exchange String,
                symbol String,
                timestamp DateTime64(3),
                price Float64,
                size Float64,
                side String,
                trade_id String
            ) ENGINE = MergeTree()
            ORDER BY (exchange, symbol, timestamp)
            """,
        ]

        if self._client:
            try:
                for sql in create_sqls:
                    self._client.execute(sql)
                logger.info("ClickHouse tables ensured")
            except Exception as e:
                logger.error("Failed to create ClickHouse tables: %s", e)

    async def write_ohlcv(self, ohlcv: Dict[str, Any]) -> None:
        """
        Write an OHLCV record.

        Args:
            ohlcv: OHLCV dict
        """
        if not self._client:
            return

        try:
            self._client.execute(
                f"""
                INSERT INTO {self.database}.{self.TABLE_OHLCV}
                (exchange, symbol, timestamp, open, high, low, close, volume, timeframe, closed)
                VALUES
                """,
                [
                    [
                        ohlcv.get("exchange", ""),
                        ohlcv.get("symbol", ""),
                        ohlcv.get("timestamp", 0) // 1000,
                        ohlcv.get("open", 0),
                        ohlcv.get("high", 0),
                        ohlcv.get("low", 0),
                        ohlcv.get("close", 0),
                        ohlcv.get("volume", 0),
                        ohlcv.get("timeframe", "1m"),
                        int(ohlcv.get("closed", True)),
                    ]
                ],
            )
        except Exception as e:
            logger.error("ClickHouse write_ohlcv error: %s", e)

    async def write_orderbook(self, symbol: str, bids: List, asks: List) -> None:
        """Write an orderbook snapshot."""
        if not self._client:
            return

        import json
        try:
            self._client.execute(
                f"""
                INSERT INTO {self.database}.{self.TABLE_ORDERBOOK}
                (exchange, symbol, timestamp, bids, asks, depth)
                VALUES
                """,
                [
                    [
                        "internal",
                        symbol,
                        int(asyncio.get_event_loop().time() * 1000) // 1000,
                        json.dumps(bids),
                        json.dumps(asks),
                        len(bids),
                    ]
                ],
            )
        except Exception as e:
            logger.error("ClickHouse write_orderbook error: %s", e)

    async def write_trade(self, trade: Dict[str, Any]) -> None:
        """Write a trade record."""
        if not self._client:
            return

        try:
            self._client.execute(
                f"""
                INSERT INTO {self.database}.{self.TABLE_TRADES}
                (exchange, symbol, timestamp, price, size, side, trade_id)
                VALUES
                """,
                [
                    [
                        trade.get("exchange", ""),
                        trade.get("symbol", ""),
                        trade.get("timestamp", 0) // 1000,
                        trade.get("price", 0),
                        trade.get("size", 0),
                        trade.get("side", "unknown"),
                        trade.get("trade_id", ""),
                    ]
                ],
            )
        except Exception as e:
            logger.error("ClickHouse write_trade error: %s", e)

    async def flush(self) -> None:
        """Flush any buffered data."""
        pass  # ClickHouse Driver handles buffering internally

    async def stop(self) -> None:
        """Stop the writer."""
        self._running = False
        if self._client:
            self._client.disconnect()
        logger.info("ClickHouseWriter stopped")
