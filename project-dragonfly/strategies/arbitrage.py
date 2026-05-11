"""Cross-exchange arbitrage strategy."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .base import Signal, SignalType, Strategy


class ArbitrageStrategy(Strategy):
    """Arbitrage strategy monitoring price differences across exchanges.

    Generates paired BUY/SELL signals when spread exceeds threshold.
    """

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.min_spread_bps: float = config.get("min_spread_bps", 15.0)
        self.max_order_size: float = config.get("max_order_size", 0.05)
        self.symbol: str = config.get("symbol", "BTC/USDT")
        self.exchange_ids: list = config.get("exchange_ids", [])
        self._prices: Dict[str, float] = {}
        self._balances: Dict[str, float] = {}

    def validate_config(self) -> bool:
        if self.min_spread_bps <= 0:
            self.logger.error("min_spread_bps must be positive")
            return False
        if self.max_order_size <= 0:
            self.logger.error("max_order_size must be positive")
            return False
        if len(self.exchange_ids) < 2:
            self.logger.error("At least two exchange_ids required for arbitrage")
            return False
        return True

    def _bps_to_decimal(self, bps: float) -> float:
        """Convert basis points to decimal fraction."""
        return bps / 10000.0

    async def on_market_data(self, data: Dict[str, Any]) -> Optional[Signal]:
        """Process market data and detect arbitrage opportunities."""
        exchange_id = data.get("exchange_id")
        symbol = data.get("symbol", self.symbol)
        price = data.get("price")

        if exchange_id is None or price is None:
            return None

        self._prices[exchange_id] = float(price)

        if len(self._prices) < 2:
            return None

        exchanges = list(self._prices.keys())
        prices = list(self._prices.values())
        max_price_exchange = exchanges[prices.index(max(prices))]
        min_price_exchange = exchanges[prices.index(min(prices))]
        max_price = max(prices)
        min_price = min(prices)

        spread_bps = ((max_price - min_price) / min_price) * 10000

        if spread_bps >= self.min_spread_bps:
            buy_exchange = min_price_exchange
            sell_exchange = max_price_exchange
            buy_price = min_price
            sell_price = max_price

            buy_balance = self._balances.get(buy_exchange, 0.0)
            size = min(self.max_order_size, buy_balance if buy_balance > 0 else self.max_order_size)

            self.logger.info(
                f"Arbitrage detected: spread={spread_bps:.2f}bps, "
                f"buy {size} {symbol} on {buy_exchange}@{buy_price}, "
                f"sell on {sell_exchange}@{sell_price}"
            )

            self._balances[buy_exchange] = self._balances.get(buy_exchange, 0.0) - size
            self._balances[sell_exchange] = self._balances.get(sell_exchange, 0.0) + size

            return Signal(
                strategy_name=self.name,
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=buy_price,
                size_percentage=size,
                client_order_id=f"arb_buy_{exchange_id}_{int(data.get('timestamp', 0))}",
            )

        return None

    async def on_order_update(self, order_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Order update: {order_update}")

    async def on_position_update(self, position_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Position update: {position_update}")

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "min_spread_bps": self.min_spread_bps,
            "max_order_size": self.max_order_size,
            "tracked_prices": self._prices,
        }