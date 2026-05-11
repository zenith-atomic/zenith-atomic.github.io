"""Base classes and enums for all trading strategies."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class StrategyMode(str, Enum):
    """Operating mode for a strategy."""

    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"


class SignalType(str, Enum):
    """Types of trading signals."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    LIQUIDATE = "liquidate"


class Signal(BaseModel):
    """A trading signal emitted by a strategy."""

    strategy_name: str
    symbol: str
    signal_type: SignalType
    price: Optional[float] = None
    size_percentage: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    take_profit_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    client_order_id: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"Signal(strategy={self.strategy_name}, symbol={self.symbol}, "
            f"type={self.signal_type.value}, price={self.price}, "
            f"size={self.size_percentage})"
        )


class Strategy(ABC):
    """Abstract base class for all trading strategies."""

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name = name
        self.config = config
        self.mode = StrategyMode(config.get("mode", StrategyMode.PAPER))
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(logging.INFO)

    @abstractmethod
    async def on_market_data(self, data: Dict[str, Any]) -> Optional[Signal]:
        """Process incoming market data and generate a signal.

        Args:
            data: Market data dictionary containing at minimum 'symbol' and 'price'.
                  May also include 'bid', 'ask', 'volume', 'timestamp', etc.

        Returns:
            A Signal if the strategy decides to act, otherwise None.
        """
        pass

    @abstractmethod
    async def on_order_update(self, order_update: Dict[str, Any]) -> None:
        """Process updates to orders from the execution layer.

        Args:
            order_update: Order update dictionary containing fields like
                          'order_id', 'status', 'filled_qty', 'avg_price', etc.
        """
        pass

    @abstractmethod
    async def on_position_update(self, position_update: Dict[str, Any]) -> None:
        """Process updates to positions from the risk management layer.

        Args:
            position_update: Position update dictionary containing fields like
                             'symbol', 'size', 'entry_price', 'unrealized_pnl', etc.
        """
        pass

    def get_metrics(self) -> Dict[str, Any]:
        """Return strategy-specific metrics for monitoring."""
        return {}

    def get_state(self) -> Dict[str, Any]:
        """Return current strategy state for persistence."""
        return {"config": self.config, "mode": self.mode.value}

    def set_state(self, state: Dict[str, Any]) -> None:
        """Restore strategy state from persistence."""
        self.config = state.get("config", self.config)
        self.mode = StrategyMode(state.get("mode", StrategyMode.PAPER))

    def validate_config(self) -> bool:
        """Validate strategy configuration parameters.

        Returns:
            True if config is valid, False otherwise.
        """
        return True