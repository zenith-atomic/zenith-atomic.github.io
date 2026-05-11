"""Market making strategy with bid/ask orders around mid-price."""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from .base import Signal, SignalType, Strategy


class MarketMakingStrategy(Strategy):
    """Market making strategy placing orders around the mid-price.

    Maintains spread from mid-price and adjusts based on order book changes.
    """

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.spread_bps: float = config.get("spread_bps", 20.0)
        self.order_size: float = config.get("order_size", 0.01)
        self.max_open_orders: int = config.get("max_open_orders", 5)
        self.symbol: str = config.get("symbol", "BTC/USDT")
        self._open_orders: List[str] = []
        self._last_mid_price: Optional[float] = None

    def validate_config(self) -> bool:
        if self.spread_bps <= 0:
            self.logger.error("spread_bps must be positive")
            return False
        if self.order_size <= 0:
            self.logger.error("order_size must be positive")
            return False
        if self.max_open_orders <= 0:
            self.logger.error("max_open_orders must be positive")
            return False
        return True

    def _calculate_spread_prices(self, mid_price: float) -> tuple[float, float]:
        """Calculate bid and ask prices from mid price."""
        half_spread = mid_price * (self.spread_bps / 10000.0) / 2.0
        return mid_price - half_spread, mid_price + half_spread

    async def on_market_data(self, data: Dict[str, Any]) -> Optional[Signal]:
        """Process market data and generate market making signals."""
        symbol = data.get("symbol", self.symbol)
        bid = data.get("bid")
        ask = data.get("ask")
        mid_price = data.get("price")

        if mid_price is None:
            if bid is not None and ask is not None:
                mid_price = (float(bid) + float(ask)) / 2.0
            else:
                return None

        mid_price = float(mid_price)

        if len(self._open_orders) >= self.max_open_orders:
            self.logger.debug(
                f"Max open orders ({self.max_open_orders}) reached, skipping"
            )
            return None

        bid_price, ask_price = self._calculate_spread_prices(mid_price)
        order_id = f"mm_{uuid.uuid4().hex[:8]}"

        self._open_orders.append(order_id)
        self._last_mid_price = mid_price

        self.logger.info(
            f"Market making: bid={bid_price:.2f}, ask={ask_price:.2f}, "
            f"mid={mid_price:.2f}, size={self.order_size}"
        )

        return Signal(
            strategy_name=self.name,
            symbol=symbol,
            signal_type=SignalType.BUY,
            price=bid_price,
            size_percentage=self.order_size,
            client_order_id=order_id,
        )

    async def on_order_update(self, order_update: Dict[str, Any]) -> None:
        """Remove filled/cancelled orders from tracking."""
        order_id = order_update.get("client_order_id") or order_update.get("order_id")
        status = order_update.get("status", "").lower()
        if order_id in self._open_orders and status in ("filled", "cancelled", "rejected"):
            self._open_orders.remove(order_id)
            self.logger.debug(f"Removed order {order_id} with status {status}")

    async def on_position_update(self, position_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Position update: {position_update}")

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "spread_bps": self.spread_bps,
            "order_size": self.order_size,
            "max_open_orders": self.max_open_orders,
            "open_orders": len(self._open_orders),
            "last_mid_price": self._last_mid_price,
        }