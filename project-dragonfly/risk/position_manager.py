"""Position manager for tracking open positions and computing P&L."""
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
import asyncio
import logging
import time
from decimal import Decimal


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class Position(BaseModel):
    """Represents a single trading position."""
    exchange_id: str
    symbol: str
    side: PositionSide
    size: Decimal
    entry_price: Decimal
    current_price: Decimal = Field(..., description="Current market price")
    unrealized_pnl: Decimal = Field(default_factory=lambda: Decimal("0"))
    realized_pnl: Decimal = Field(default_factory=lambda: Decimal("0"))
    timestamp: float = Field(default_factory=time.time)

    def model_post_init(self, *args, **kwargs):
        self._recompute_unrealized_pnl()

    def _recompute_unrealized_pnl(self) -> None:
        """Recompute unrealized P&L based on current price."""
        if self.side == PositionSide.LONG:
            pnl = (self.current_price - self.entry_price) * self.size
        elif self.side == PositionSide.SHORT:
            pnl = (self.entry_price - self.current_price) * self.size
        else:
            pnl = Decimal("0")
        object.__setattr__(self, 'unrealized_pnl', pnl)


class PositionManager:
    """
    Manages all open positions and computes portfolio P&L.
    Thread-safe for async operations.
    """

    def __init__(self, initial_capital: Decimal = Decimal("100000")):
        self.positions: Dict[str, Position] = {}  # key: f"{exchange_id}:{symbol}"
        self.total_capital = initial_capital
        self.available_capital = initial_capital
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"PositionManager initialized with capital: {initial_capital}")

    def _position_key(self, exchange_id: str, symbol: str) -> str:
        """Generate a unique key for a position."""
        return f"{exchange_id}:{symbol}"

    async def update_position(
        self,
        exchange_id: str,
        symbol: str,
        side: PositionSide,
        size: Decimal,
        entry_price: Decimal,
        current_price: Decimal,
    ) -> Position:
        """
        Create or update a position. Computes unrealized P&L.

        Args:
            exchange_id: Exchange identifier (e.g., "binance", "kraken")
            symbol: Trading pair symbol (e.g., "BTC/USDT")
            side: Position side (LONG, SHORT, or FLAT)
            size: Position size in base currency
            entry_price: Entry price for the position
            current_price: Current market price

        Returns:
            The updated Position object
        """
        async with self._lock:
            key = self._position_key(exchange_id, symbol)
            timestamp = time.time()

            if side == PositionSide.FLAT:
                self.logger.debug(f"Flat position for {key}, removing from tracker")
                if key in self.positions:
                    del self.positions[key]
                return Position(
                    exchange_id=exchange_id,
                    symbol=symbol,
                    side=PositionSide.FLAT,
                    size=Decimal("0"),
                    entry_price=Decimal("0"),
                    current_price=current_price,
                    timestamp=timestamp,
                )

            if key in self.positions:
                pos = self.positions[key]
                # Average into the position
                total_size = pos.size + size
                if total_size > 0:
                    avg_price = (pos.entry_price * pos.size + entry_price * size) / total_size
                    object.__setattr__(pos, 'entry_price', avg_price)
                    object.__setattr__(pos, 'size', total_size)
                    object.__setattr__(pos, 'current_price', current_price)
                    object.__setattr__(pos, 'side', side)
                    object.__setattr__(pos, 'timestamp', timestamp)
                    pos._recompute_unrealized_pnl()
                    self.logger.info(
                        f"Updated position {key}: side={side}, size={total_size}, "
                        f"avg_price={avg_price}, unrealized_pnl={pos.unrealized_pnl}"
                    )
                return pos
            else:
                pos = Position(
                    exchange_id=exchange_id,
                    symbol=symbol,
                    side=side,
                    size=size,
                    entry_price=entry_price,
                    current_price=current_price,
                    timestamp=timestamp,
                )
                self.positions[key] = pos
                self.logger.info(
                    f"Created new position {key}: side={side}, size={size}, "
                    f"entry_price={entry_price}"
                )
                return pos

    async def close_position(
        self,
        exchange_id: str,
        symbol: str,
        close_price: Decimal,
    ) -> Position:
        """
        Close a position and compute realized P&L.

        Args:
            exchange_id: Exchange identifier
            symbol: Trading pair symbol
            close_price: Price at which to close the position

        Returns:
            The closed Position object with realized P&L
        """
        async with self._lock:
            key = self._position_key(exchange_id, symbol)
            if key not in self.positions:
                self.logger.warning(f"Attempted to close non-existent position: {key}")
                return Position(
                    exchange_id=exchange_id,
                    symbol=symbol,
                    side=PositionSide.FLAT,
                    size=Decimal("0"),
                    entry_price=Decimal("0"),
                    current_price=close_price,
                    timestamp=time.time(),
                )

            pos = self.positions[key]

            # Compute realized P&L
            if pos.side == PositionSide.LONG:
                realized = (close_price - pos.entry_price) * pos.size
            elif pos.side == PositionSide.SHORT:
                realized = (pos.entry_price - close_price) * pos.size
            else:
                realized = Decimal("0")

            # Update realized P&L
            total_realized = pos.realized_pnl + realized
            object.__setattr__(pos, 'realized_pnl', total_realized)
            object.__setattr__(pos, 'current_price', close_price)
            object.__setattr__(pos, 'unrealized_pnl', Decimal("0"))
            object.__setattr__(pos, 'side', PositionSide.FLAT)

            # Free up capital (simplified - actual implementation would track margin)
            self.available_capital += realized
            self.total_capital += realized

            self.logger.info(
                f"Closed position {key}: realized_pnl={realized}, "
                f"total_capital={self.total_capital}"
            )

            # Remove from active positions
            del self.positions[key]

            return pos

    def get_position(self, exchange_id: str, symbol: str) -> Optional[Position]:
        """Get a specific position by exchange and symbol."""
        key = self._position_key(exchange_id, symbol)
        return self.positions.get(key)

    def get_all_positions(self) -> List[Position]:
        """Get all open positions."""
        return list(self.positions.values())

    def get_total_equity(self) -> Decimal:
        """
        Calculate total portfolio equity including unrealized P&L.
        """
        total = self.total_capital
        for pos in self.positions.values():
            total += pos.unrealized_pnl
        return total

    def get_available_capital(self) -> Decimal:
        """Get available capital for new trades."""
        return self.available_capital

    async def handle_trade(self, trade: Dict[str, Any]) -> None:
        """
        Update positions based on a trade execution event.

        Expected trade dict format:
        {
            "exchange_id": str,
            "symbol": str,
            "side": "buy" | "sell",
            "size": Decimal,
            "price": Decimal,
            "timestamp": float (optional)
        }
        """
        try:
            exchange_id = trade["exchange_id"]
            symbol = trade["symbol"]
            side = trade["side"].lower()
            size = Decimal(str(trade["size"]))
            price = Decimal(str(trade["price"]))

            if side == "buy":
                position_side = PositionSide.LONG
            elif side == "sell":
                position_side = PositionSide.SHORT
            else:
                self.logger.error(f"Unknown trade side: {side}")
                return

            await self.update_position(
                exchange_id=exchange_id,
                symbol=symbol,
                side=position_side,
                size=size,
                entry_price=price,
                current_price=price,
            )
            self.logger.info(f"Handled trade: {exchange_id} {symbol} {side} {size}@{price}")
        except Exception as e:
            self.logger.exception(f"Error handling trade: {e}")

    async def handle_market_data(self, data: Dict[str, Any]) -> None:
        """
        Update current prices for open positions based on market data.

        Expected data dict format:
        {
            "symbol": str,
            "price": Decimal,
            "exchange_id": str (optional, updates all exchanges if omitted)
        }
        """
        try:
            symbol = data["symbol"]
            price = Decimal(str(data["price"]))
            exchange_id = data.get("exchange_id")

            # Update all positions for this symbol or specific exchange
            for key, pos in list(self.positions.items()):
                if pos.symbol == symbol:
                    if exchange_id is None or pos.exchange_id == exchange_id:
                        object.__setattr__(pos, 'current_price', price)
                        pos._recompute_unrealized_pnl()

            self.logger.debug(f"Updated market data: {symbol} @{price}")
        except Exception as e:
            self.logger.exception(f"Error handling market data: {e}")

    def get_total_unrealized_pnl(self) -> Decimal:
        """Get sum of all unrealized P&Ls."""
        return sum(pos.unrealized_pnl for pos in self.positions.values())

    def get_total_realized_pnl(self) -> Decimal:
        """Get sum of all realized P&Ls."""
        return sum(pos.realized_pnl for pos in self.positions.values())
