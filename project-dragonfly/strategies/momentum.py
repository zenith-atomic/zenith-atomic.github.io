"""Momentum strategy using moving average crossover."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Signal, SignalType, Strategy, StrategyMode


class MomentumStrategy(Strategy):
    """Momentum strategy based on short/long moving average crossover.

    Generates BUY when short MA crosses above long MA.
    Generates SELL when short MA crosses below long MA.
    """

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.short_period: int = config.get("short_period", 10)
        self.long_period: int = config.get("long_period", 30)
        self.size_percentage: float = config.get("size_percentage", 0.1)
        self.symbol: str = config.get("symbol", "BTC/USDT")
        self._price_history: List[float] = []
        self._last_signal: Optional[SignalType] = None

    def validate_config(self) -> bool:
        if self.short_period <= 0:
            self.logger.error("short_period must be positive")
            return False
        if self.long_period <= self.short_period:
            self.logger.error("long_period must be greater than short_period")
            return False
        if not (0.0 < self.size_percentage <= 1.0):
            self.logger.error("size_percentage must be in (0, 1]")
            return False
        return True

    def _calculate_ma(self, prices: List[float], period: int) -> Optional[float]:
        """Calculate simple moving average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    async def on_market_data(self, data: Dict[str, Any]) -> Optional[Signal]:
        """Process market data and generate crossover signals."""
        symbol = data.get("symbol", self.symbol)
        price = data.get("price")
        if price is None:
            self.logger.warning("No price in market data")
            return None

        self._price_history.append(float(price))
        max_len = self.long_period + 10
        if len(self._price_history) > max_len:
            self._price_history = self._price_history[-max_len:]

        short_ma = self._calculate_ma(self._price_history, self.short_period)
        long_ma = self._calculate_ma(self._price_history, self.long_period)

        if short_ma is None or long_ma is None:
            return None

        signal_type: SignalType
        if short_ma > long_ma and self._last_signal != SignalType.BUY:
            signal_type = SignalType.BUY
        elif short_ma < long_ma and self._last_signal != SignalType.SELL:
            signal_type = SignalType.SELL
        else:
            return None

        self._last_signal = signal_type
        self.logger.info(
            f"Crossover detected: {signal_type.value} at price={price}, "
            f"short_ma={short_ma:.2f}, long_ma={long_ma:.2f}"
        )

        return Signal(
            strategy_name=self.name,
            symbol=symbol,
            signal_type=signal_type,
            price=float(price),
            size_percentage=self.size_percentage,
            stop_loss_price=(
                float(price) * 0.98 if signal_type == SignalType.BUY
                else float(price) * 1.02
            ),
            take_profit_price=(
                float(price) * 1.05 if signal_type == SignalType.BUY
                else float(price) * 0.95
            ),
        )

    async def on_order_update(self, order_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Order update: {order_update}")

    async def on_position_update(self, position_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Position update: {position_update}")

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "short_period": self.short_period,
            "long_period": self.long_period,
            "size_percentage": self.size_percentage,
            "prices_collected": len(self._price_history),
        }