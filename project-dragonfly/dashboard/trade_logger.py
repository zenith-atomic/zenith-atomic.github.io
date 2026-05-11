"""
Trade logging module for Project Dragonfly.

Provides centralized trade logging with Pydantic models and asyncio support.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class TradeLogEntry(BaseModel):
    """Represents a single trade log entry.

    Attributes:
        trade_id: Unique identifier for the trade.
        strategy_name: Name of the strategy that generated the trade.
        symbol: Trading pair symbol (e.g., "BTC/USDT").
        side: Trade direction - "buy" or "sell".
        amount: Quantity of the asset traded.
        price: Execution price per unit.
        timestamp: Unix timestamp when the trade occurred.
        pnl_usd: Profit/loss in USD.
        fee_usd: Trading fee in USD.
    """

    trade_id: str = Field(..., description="Unique trade identifier")
    strategy_name: str = Field(..., description="Name of the trading strategy")
    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="Trade direction: buy or sell")
    amount: Decimal = Field(..., description="Quantity traded")
    price: Decimal = Field(..., description="Execution price per unit")
    timestamp: float = Field(..., description="Unix timestamp")
    pnl_usd: Decimal = Field(default=Decimal("0"), description="Profit/loss in USD")
    fee_usd: Decimal = Field(default=Decimal("0"), description="Trading fee in USD")

    class Config:
        """Pydantic configuration."""

        arbitrary_types_allowed = True


class TradeLogger:
    """Centralized trade logger with async support.

    Provides methods to log trades, retrieve trade history, and persist
    trade data for auditing and analysis.
    """

    def __init__(self) -> None:
        """Initialize the TradeLogger with an empty trade log."""
        self._trade_log: List[TradeLogEntry] = []
        self._logger = logging.getLogger(self.__class__.__name__)

    async def log_trade(self, trade: TradeLogEntry) -> None:
        """Log a trade entry.

        Args:
            trade: The trade entry to log.
        """
        self._trade_log.append(trade)
        self._logger.info(
            "Trade logged: %s %s %s %s @ %s P&L: %s Fee: %s",
            trade.strategy_name,
            trade.side,
            trade.amount,
            trade.symbol,
            trade.price,
            trade.pnl_usd,
            trade.fee_usd,
        )

    def get_trade_history(self, limit: int = 100) -> List[TradeLogEntry]:
        """Retrieve recent trade history.

        Args:
            limit: Maximum number of trades to return. Defaults to 100.

        Returns:
            List of recent trade entries, newest first.
        """
        return self._trade_log[-limit:]

    def get_total_pnl(self) -> Decimal:
        """Calculate total P&L across all logged trades.

        Returns:
            Sum of all trade P&Ls.
        """
        return sum((trade.pnl_usd for trade in self._trade_log), Decimal("0"))