"""Mean reversion strategy using Bollinger Bands."""
from __future__ import annotations

import statistics
from typing import Any, Dict, List, Optional

from .base import Signal, SignalType, Strategy


class MeanReversionStrategy(Strategy):
    """Mean reversion strategy using Bollinger Bands.

    Generates BUY when price touches lower band (oversold).
    Generates SELL when price touches upper band (overbought).
    """

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.period: int = config.get("period", 20)
        self.num_std_dev: float = config.get("num_std_dev", 2.0)
        self.size_percentage: float = config.get("size_percentage", 0.1)
        self.symbol: str = config.get("symbol", "BTC/USDT")
        self._price_history: List[float] = []
        self._last_signal: Optional[SignalType] = None

    def validate_config(self) -> bool:
        if self.period <= 1:
            self.logger.error("period must be at least 2")
            return False
        if self.num_std_dev <= 0:
            self.logger.error("num_std_dev must be positive")
            return False
        if not (0.0 < self.size_percentage <= 1.0):
            self.logger.error("size_percentage must be in (0, 1]")
            return False
        return True

    def _calculate_bollinger_bands(
        self, prices: List[float]
    ) -> Optional[tuple[float, float, float]]:
        """Calculate Bollinger Bands (middle, upper, lower)."""
        if len(prices) < self.period:
            return None

        window = prices[-self.period :]
        middle = statistics.mean(window)
        std_dev = statistics.stdev(window)
        upper = middle + (std_dev * self.num_std_dev)
        lower = middle - (std_dev * self.num_std_dev)
        return middle, upper, lower

    async def on_market_data(self, data: Dict[str, Any]) -> Optional[Signal]:
        """Process market data and generate mean reversion signals."""
        symbol = data.get("symbol", self.symbol)
        price = data.get("price")

        if price is None:
            self.logger.warning("No price in market data")
            return None

        price = float(price)
        self._price_history.append(price)
        if len(self._price_history) > self.period * 3:
            self._price_history = self._price_history[-(self.period * 3) :]

        bands = self._calculate_bollinger_bands(self._price_history)
        if bands is None:
            return None

        middle, upper, lower = bands

        signal_type: Optional[SignalType] = None
        if price <= lower and self._last_signal != SignalType.BUY:
            signal_type = SignalType.BUY
            self.logger.info(
                f"Lower band touched: price={price:.2f}, lower={lower:.2f}"
            )
        elif price >= upper and self._last_signal != SignalType.SELL:
            signal_type = SignalType.SELL
            self.logger.info(
                f"Upper band touched: price={price:.2f}, upper={upper:.2f}"
            )

        if signal_type is None:
            return None

        self._last_signal = signal_type

        return Signal(
            strategy_name=self.name,
            symbol=symbol,
            signal_type=signal_type,
            price=price,
            size_percentage=self.size_percentage,
            stop_loss_price=(
                lower * 0.98 if signal_type == SignalType.BUY
                else upper * 1.02
            ),
            take_profit_price=(
                middle if signal_type == SignalType.BUY else middle
            ),
        )

    async def on_order_update(self, order_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Order update: {order_update}")

    async def on_position_update(self, position_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Position update: {position_update}")

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "period": self.period,
            "num_std_dev": self.num_std_dev,
            "size_percentage": self.size_percentage,
            "prices_collected": len(self._price_history),
        }