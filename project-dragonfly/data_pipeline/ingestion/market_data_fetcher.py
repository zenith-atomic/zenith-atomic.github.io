"""Fetches live market data from exchanges via CCXT."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
import aiohttp
import ccxt
from ccxt import Exchange

from data_pipeline.normalizer import OHLCV, OrderBook, Trade, normalize_ohlcv, normalize_orderbook, normalize_trade

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """
    Fetches live market data from exchanges via CCXT.

    Supports WebSocket connections with REST fallback.
    Emits normalized data to a shared asyncio Queue.
    """

    def __init__(self, exchange_ids: List[str], queue: asyncio.Queue, config: Optional[Dict[str, Any]] = None):
        """
        Initialize MarketDataFetcher.

        Args:
            exchange_ids: List of exchange IDs (e.g. ['binance', 'hyperliquid'])
            queue: asyncio.Queue to emit normalized data to
            config: Optional exchange configuration dict
        """
        self.exchange_ids = exchange_ids
        self.queue = queue
        self.config = config or {}
        self._exchanges: Dict[str, Exchange] = {}
        self._ws_connections: Dict[str, Any] = {}
        self._running = False
        self._retry_delays = {eid: 1.0 for eid in exchange_ids}
        self._max_retry_delay = 60.0

    async def start(self) -> None:
        """Start fetching data from all configured exchanges."""
        self._running = True

        for eid in self.exchange_ids:
            exchange = await self._init_exchange(eid)
            if exchange:
                self._exchanges[eid] = exchange

        await asyncio.gather(*[self._run_exchange(eid) for eid in self._exchanges.keys()])

    async def _init_exchange(self, exchange_id: str) -> Optional[Exchange]:
        """Initialize a CCXT exchange instance."""
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({
                "enableRateLimit": True,
                "options": {"defaultType": "spot"},
            })
            await asyncio.to_thread(exchange.load_markets)
            logger.info("Initialized exchange: %s", exchange_id)
            return exchange
        except Exception as e:
            logger.error("Failed to initialize exchange %s: %s", exchange_id, e)
            return None

    async def _run_exchange(self, exchange_id: str) -> None:
        """Run data fetching loop for a single exchange."""
        exchange = self._exchanges.get(exchange_id)
        if not exchange:
            return

        symbols = self.config.get(exchange_id, {}).get("symbols", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])

        while self._running:
            try:
                # Try WebSocket first, fall back to REST
                ws_success = await self._try_websocket(exchange_id, exchange, symbols)
                if not ws_success:
                    await self._rest_polling_fallback(exchange_id, exchange, symbols)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in exchange loop for %s: %s", exchange_id, e)
                await asyncio.sleep(self._retry_delays[exchange_id])
                self._retry_delays[exchange_id] = min(self._retry_delays[exchange_id] * 2, self._max_retry_delay)

    async def _try_websocket(self, exchange_id: str, exchange: Exchange, symbols: List[str]) -> bool:
        """Attempt WebSocket connection. Returns True if successful."""
        try:
            # CCXT has a WebSocket API - use it if available
            if hasattr(exchange, "watch_ohlcv"):
                await asyncio.gather(*[
                    asyncio.to_thread(exchange.watch_ohlcv, symbol, "1m")
                    for symbol in symbols
                ])
            logger.info("WebSocket active for %s", exchange_id)
            return True
        except Exception as e:
            logger.warning("WebSocket not available for %s: %s", exchange_id, e)
            return False

    async def _rest_polling_fallback(self, exchange_id: str, exchange: Exchange, symbols: List[str]) -> None:
        """REST polling fallback when WebSocket fails."""
        for symbol in symbols:
            try:
                ohlcv_data = await asyncio.to_thread(exchange.fetch_ohlcv, symbol, "1m")
                for raw in ohlcv_data[-1:]:  # Just latest candle
                    ohlcv = normalize_ohlcv(exchange_id, raw, symbol, "1m")
                    await self.queue.put(("ohlcv", ohlcv.to_dict()))

                # Orderbook
                ob_data = await asyncio.to_thread(exchange.fetch_order_book, symbol, 20)
                ob = normalize_orderbook(
                    exchange_id,
                    symbol,
                    ob_data.get("bids", []),
                    ob_data.get("asks", []),
                )
                await self.queue.put(("orderbook", ob.to_dict()))

                await asyncio.sleep(0.5)  # Rate limit

            except Exception as e:
                logger.error("REST polling error for %s/%s: %s", exchange_id, symbol, e)

    async def fetch_ohlcv(self, symbol: str, timeframe: str = "1m") -> Optional[List[OHLCV]]:
        """
        Fetch OHLCV data for a symbol via REST.

        Args:
            symbol: Trading pair (e.g. 'BTC/USDT')
            timeframe: Candle timeframe

        Returns:
            List of OHLCV objects
        """
        results = []
        for eid, exchange in self._exchanges.items():
            try:
                raw_data = await asyncio.to_thread(exchange.fetch_ohlcv, symbol, timeframe)
                for raw in raw_data:
                    ohlcv = normalize_ohlcv(eid, raw, symbol, timeframe)
                    results.append(ohlcv)
            except Exception as e:
                logger.error("fetch_ohlcv error for %s/%s: %s", eid, symbol, e)
        return results

    async def fetch_orderbook(self, symbol: str) -> Optional[OrderBook]:
        """
        Fetch orderbook for a symbol via REST.

        Args:
            symbol: Trading pair

        Returns:
            OrderBook object
        """
        for eid, exchange in self._exchanges.items():
            try:
                data = await asyncio.to_thread(exchange.fetch_order_book, symbol, 20)
                return normalize_orderbook(eid, symbol, data.get("bids", []), data.get("asks", []))
            except Exception as e:
                logger.error("fetch_orderbook error for %s/%s: %s", eid, symbol, e)
        return None

    def handle_message(self, exchange_id: str, msg: Dict[str, Any]) -> None:
        """
        Handle incoming WebSocket message.

        Args:
            exchange_id: Exchange identifier
            msg: Raw message dict
        """
        try:
            if "e" in msg and msg["e"] == "kline":
                symbol = msg.get("s", "")
                raw_ohlcv = [
                    msg["k"]["t"],
                    float(msg["k"]["o"]),
                    float(msg["k"]["h"]),
                    float(msg["k"]["l"]),
                    float(msg["k"]["c"]),
                    float(msg["k"]["v"]),
                ]
                ohlcv = normalize_ohlcv(exchange_id, raw_ohlcv, symbol, msg["k"]["i"])
                asyncio.create_task(self.queue.put(("ohlcv", ohlcv.to_dict())))

            elif "e" in msg and msg["e"] == "depthUpdate":
                symbol = msg.get("s", "")
                ob = normalize_orderbook(
                    exchange_id,
                    symbol,
                    msg.get("b", []),
                    msg.get("a", []),
                )
                asyncio.create_task(self.queue.put(("orderbook", ob.to_dict())))

        except Exception as e:
            logger.error("handle_message error for %s: %s", exchange_id, e)

    async def stop(self) -> None:
        """Stop all data fetching."""
        self._running = False
        for ws in self._ws_connections.values():
            try:
                await ws.close()
            except Exception:
                pass
        logger.info("MarketDataFetcher stopped")
