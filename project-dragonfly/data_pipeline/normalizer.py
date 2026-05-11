"""Data models and normalization for Project Dragonfly."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class OHLCV:
    """Normalized OHLCV (candle) data."""
    exchange: str
    symbol: str
    timestamp: int  # milliseconds
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "1m"
    closed: bool = True

    @property
    def datetime(self) -> datetime:
        return datetime.utcfromtimestamp(self.timestamp / 1000)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "timeframe": self.timeframe,
            "closed": self.closed,
        }


@dataclass
class OrderBook:
    """Normalized orderbook data."""
    exchange: str
    symbol: str
    timestamp: int
    bids: List[Tuple[float, float]]  # [(price, size), ...]
    asks: List[Tuple[float, float]]
    depth: int = 20

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "bids": self.bids,
            "asks": self.asks,
            "depth": self.depth,
        }


@dataclass
class Trade:
    """Normalized trade data."""
    exchange: str
    symbol: str
    timestamp: int
    price: float
    size: float
    side: str  # "buy" or "sell"
    trade_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "price": self.price,
            "size": self.size,
            "side": self.side,
            "trade_id": self.trade_id,
        }


def normalize_ohlcv(exchange: str, raw: Dict[str, Any], symbol: str = "", timeframe: str = "1m") -> OHLCV:
    """
    Normalize raw OHLCV data from any exchange into standard OHLCV model.

    Args:
        exchange: Exchange identifier (e.g. 'binance', 'hyperliquid')
        raw: Raw OHLCV data from exchange (list [t,o,h,l,c,v] or dict)
        symbol: Trading pair symbol
        timeframe: Candle timeframe

    Returns:
        Normalized OHLCV instance
    """
    try:
        if isinstance(raw, list):
            # CCXT format: [timestamp, open, high, low, close, volume]
            timestamp = int(raw[0]) if raw[0] is not None else int(datetime.utcnow().timestamp() * 1000)
            return OHLCV(
                exchange=exchange,
                symbol=symbol,
                timestamp=timestamp,
                open=float(raw[1]),
                high=float(raw[2]),
                low=float(raw[3]),
                close=float(raw[4]),
                volume=float(raw[5]),
                timeframe=timeframe,
                closed=True,
            )
        elif isinstance(raw, dict):
            # Dict-based format
            ts = raw.get("timestamp") or raw.get("ts") or raw.get("time")
            return OHLCV(
                exchange=exchange,
                symbol=symbol or raw.get("symbol", ""),
                timestamp=int(ts) if ts else int(datetime.utcnow().timestamp() * 1000),
                open=float(raw.get("open", raw.get("o", 0))),
                high=float(raw.get("high", raw.get("h", 0))),
                low=float(raw.get("low", raw.get("l", 0))),
                close=float(raw.get("close", raw.get("c", 0))),
                volume=float(raw.get("volume", raw.get("v", 0))),
                timeframe=timeframe,
                closed=raw.get("closed", True),
            )
        else:
            raise ValueError(f"Unsupported OHLCV format: {type(raw)}")
    except Exception as e:
        logger.warning("Failed to normalize OHLCV from %s: %s", exchange, e)
        raise


def normalize_orderbook(
    exchange: str, symbol: str, bids: List[Any], asks: List[Any], depth: int = 20
) -> OrderBook:
    """
    Normalize raw orderbook data into standard OrderBook model.

    Args:
        exchange: Exchange identifier
        symbol: Trading pair symbol
        bids: List of bid [price, size] pairs
        asks: List of ask [price, size] pairs
        depth: Max depth to retain

    Returns:
        Normalized OrderBook instance
    """
    normalized_bids = []
    normalized_asks = []

    for bid in bids[:depth]:
        if isinstance(bid, (list, tuple)):
            normalized_bids.append((float(bid[0]), float(bid[1])))
        elif isinstance(bid, dict):
            normalized_bids.append((float(bid.get("price", 0)), float(bid.get("size", bid.get("amount", 0)))))

    for ask in asks[:depth]:
        if isinstance(ask, (list, tuple)):
            normalized_asks.append((float(ask[0]), float(ask[1])))
        elif isinstance(ask, dict):
            normalized_asks.append((float(ask.get("price", 0)), float(ask.get("size", ask.get("amount", 0)))))

    return OrderBook(
        exchange=exchange,
        symbol=symbol,
        timestamp=int(datetime.utcnow().timestamp() * 1000),
        bids=normalized_bids,
        asks=normalized_asks,
        depth=depth,
    )


def normalize_trade(exchange: str, raw: Dict[str, Any], symbol: str = "") -> Trade:
    """
    Normalize raw trade data from any exchange into standard Trade model.

    Args:
        exchange: Exchange identifier
        raw: Raw trade data from exchange
        symbol: Trading pair symbol

    Returns:
        Normalized Trade instance
    """
    try:
        if isinstance(raw, list):
            # CCXT format: [timestamp, price, size, side]
            return Trade(
                exchange=exchange,
                symbol=symbol,
                timestamp=int(raw[0]) if raw[0] is not None else int(datetime.utcnow().timestamp() * 1000),
                price=float(raw[1]),
                size=float(raw[2]),
                side=str(raw[3]) if len(raw) > 3 else "unknown",
            )
        elif isinstance(raw, dict):
            side = raw.get("side", raw.get("S", "unknown"))
            if isinstance(side, str):
                side = side.lower()
            return Trade(
                exchange=exchange,
                symbol=symbol or raw.get("symbol", ""),
                timestamp=int(raw.get("timestamp", raw.get("ts", datetime.utcnow().timestamp() * 1000))),
                price=float(raw.get("price", raw.get("p", 0))),
                size=float(raw.get("size", raw.get("size", raw.get("amount", raw.get("q", 0))))),
                side=side,
                trade_id=raw.get("id") or raw.get("trade_id"),
            )
        else:
            raise ValueError(f"Unsupported trade format: {type(raw)}")
    except Exception as e:
        logger.warning("Failed to normalize trade from %s: %s", exchange, e)
        raise
