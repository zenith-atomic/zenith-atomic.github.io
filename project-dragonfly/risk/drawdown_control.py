"""Drawdown control monitor for portfolio risk management."""
from typing import Dict, Any
import logging
from decimal import Decimal
import asyncio

from .position_manager import PositionManager


class DrawdownControl:
    """
    Monitors portfolio drawdown and triggers circuit breakers if thresholds are breached.

    Tracks peak equity and computes current drawdown percentage.
    When drawdown exceeds max_drawdown_percent, can halt trading.
    """

    def __init__(self, config: Dict[str, Any], position_manager: PositionManager):
        """
        Initialize drawdown control.

        Args:
            config: Drawdown configuration dict
            position_manager: Shared PositionManager instance
        """
        self.config = config
        self.position_manager = position_manager
        self.max_drawdown_percent = Decimal(
            str(config.get("max_drawdown_percent", 0.20))
        )
        self.stop_trading_on_breach = config.get("stop_trading_on_breach", True)

        # Initialize equity tracking
        self.initial_equity = position_manager.total_capital
        self.peak_equity = self.initial_equity
        self.is_breached = False
        self.breach_timestamp: float = 0.0

        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(
            f"DrawdownControl initialized: max={self.max_drawdown_percent * 100}%, "
            f"initial_equity={self.initial_equity}, "
            f"stop_on_breach={self.stop_trading_on_breach}"
        )

    async def update_equity(self) -> Decimal:
        """
        Update peak equity and check for drawdown breaches.

        This should be called periodically (e.g., on each market data tick)
        to keep peak equity and breach status current.

        Returns:
            Current total equity
        """
        async with self._lock:
            current_equity = self.position_manager.get_total_equity()

            # Update peak equity if current is higher
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
                self.logger.debug(f"New peak equity: {self.peak_equity}")

            # Check for breach
            drawdown = self.peak_equity - current_equity
            drawdown_percent = (
                drawdown / self.peak_equity if self.peak_equity > 0 else Decimal("0")
            )

            if drawdown_percent > self.max_drawdown_percent and not self.is_breached:
                self.is_breached = True
                import time
                self.breach_timestamp = time.time()
                self.logger.warning(
                    f"DRAWDOWN BREACH DETECTED: {drawdown_percent * 100:.2f}% "
                    f"(max {self.max_drawdown_percent * 100}%) - "
                    f"current=${current_equity}, peak=${self.peak_equity}, "
                    f"drop=${drawdown}"
                )
            elif self.is_breached and drawdown_percent <= self.max_drawdown_percent:
                self.logger.info(
                    f"Drawdown recovered: {drawdown_percent * 100:.2f}% "
                    f"is now below threshold"
                )

            return current_equity

    def get_current_drawdown(self) -> Decimal:
        """
        Calculate current drawdown as a Decimal fraction.

        Returns:
            Current drawdown percentage (e.g., Decimal("0.05") for 5%)
        """
        current_equity = self.position_manager.get_total_equity()
        if self.peak_equity <= 0:
            return Decimal("0")
        drawdown = self.peak_equity - current_equity
        if drawdown <= 0:
            return Decimal("0")
        return drawdown / self.peak_equity

    def get_drawdown_amount(self) -> Decimal:
        """
        Get the absolute drawdown amount in dollars.

        Returns:
            Drawdown amount (positive number representing loss from peak)
        """
        current_equity = self.position_manager.get_total_equity()
        drawdown = self.peak_equity - current_equity
        return max(Decimal("0"), drawdown)

    def is_drawdown_breached(self) -> bool:
        """
        Check if current drawdown exceeds the maximum threshold.

        Returns:
            True if drawdown breach is active
        """
        return self.is_breached

    def reset_breach(self) -> None:
        """
        Manually reset breach status (e.g., after manual intervention).
        """
        self.is_breached = False
        self.breach_timestamp = 0.0
        self.logger.info("Drawdown breach manually reset")

    def reset_peak(self) -> None:
        """
        Reset peak equity to current equity (start fresh tracking).
        """
        current_equity = self.position_manager.get_total_equity()
        self.peak_equity = current_equity
        self.is_breached = False
        self.breach_timestamp = 0.0
        self.logger.info(f"Peak equity reset to current: {self.peak_equity}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get a snapshot of drawdown control status.

        Returns:
            Dict with equity, peak, drawdown, and breach info
        """
        current = self.position_manager.get_total_equity()
        drawdown_pct = self.get_current_drawdown()
        drawdown_amt = self.get_drawdown_amount()
        return {
            "current_equity": str(current),
            "peak_equity": str(self.peak_equity),
            "initial_equity": str(self.initial_equity),
            "drawdown_percent": str(drawdown_pct),
            "drawdown_amount": str(drawdown_amt),
            "max_drawdown_percent": str(self.max_drawdown_percent),
            "is_breached": self.is_breached,
            "stop_trading_on_breach": self.stop_trading_on_breach,
        }
