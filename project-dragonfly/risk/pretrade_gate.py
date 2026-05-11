"""Pre-trade risk gate that enforces position, exposure, and drawdown limits."""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging
from decimal import Decimal

from .position_manager import PositionManager, PositionSide


class RiskCheckResult(BaseModel):
    """Result of a single risk check."""
    passed: bool
    reason: Optional[str] = Field(default=None)

    def __bool__(self) -> bool:
        return self.passed


class PreTradeGate:
    """
    Enforces pre-trade risk checks before any order is submitted.
    
    Checks performed:
    - Position size limits per symbol
    - Total exposure limits
    - Per-exchange exposure limits
    - Drawdown limits
    """

    def __init__(self, config: Dict[str, Any], position_manager: PositionManager):
        """
        Initialize the pre-trade gate.

        Args:
            config: Risk configuration dict loaded from YAML
            position_manager: Shared PositionManager instance
        """
        self.config = config
        self.position_manager = position_manager
        self.logger = logging.getLogger(self.__class__.__name__)

        # Load position limits
        position_limits_raw = config.get("position_limits", {})
        self.position_limits: Dict[str, Dict[str, Decimal]] = {}
        for symbol, limits in position_limits_raw.items():
            self.position_limits[symbol] = {
                "max_size_usd": Decimal(str(limits.get("max_size_usd", 0))),
                "max_leverage": Decimal(str(limits.get("max_leverage", 1))),
            }

        # Load exposure limits
        exposure_cfg = config.get("exposure_limits", {})
        self.total_max_exposure = Decimal(str(exposure_cfg.get("total_max_usd", 20000)))
        self.max_exposure_per_exchange = Decimal(
            str(exposure_cfg.get("max_exposure_per_exchange_usd", 15000))
        )

        # Load drawdown limits
        drawdown_cfg = config.get("drawdown_control", {})
        self.max_drawdown_percent = Decimal(
            str(drawdown_cfg.get("max_drawdown_percent", 0.20))
        )

        self.logger.info(
            f"PreTradeGate initialized: total_max={self.total_max_exposure}, "
            f"per_exchange_max={self.max_exposure_per_exchange}, "
            f"max_drawdown={self.max_drawdown_percent * 100}%"
        )

    async def run_checks(self, order_request: Dict[str, Any]) -> RiskCheckResult:
        """
        Run all risk checks for a given order request.

        Args:
            order_request: Order details with keys:
                - symbol: str (e.g., "BTC/USDT")
                - side: str ("buy" or "sell")
                - size: Decimal or float (in base currency)
                - price: Decimal or float (optional, for USD calc)
                - exchange_id: str (optional, defaults to "default")

        Returns:
            RiskCheckResult with passed=True if all checks pass
        """
        symbol = order_request.get("symbol", "UNKNOWN")
        exchange_id = order_request.get("exchange_id", "default")
        size = Decimal(str(order_request.get("size", 0)))
        price = Decimal(str(order_request.get("price", 0)))
        order_value_usd = size * price

        self.logger.debug(
            f"Running risk checks for {exchange_id}:{symbol} "
            f"{order_request.get('side')} {size}@{price} (${order_value_usd})"
        )

        # Run all checks in sequence; fail fast on first rejection
        checks = [
            self._check_position_limits(order_request, symbol, size, price, order_value_usd),
            self._check_exposure_limits(order_request, exchange_id, symbol, order_value_usd),
            self._check_drawdown_limits(order_request),
        ]

        for check_coro in checks:
            result = await check_coro
            if not result.passed:
                self.logger.warning(
                    f"Risk check failed for {exchange_id}:{symbol}: {result.reason}"
                )
                return result

        self.logger.info(f"All risk checks passed for {exchange_id}:{symbol}")
        return RiskCheckResult(passed=True)

    async def _check_position_limits(
        self,
        order_request: Dict[str, Any],
        symbol: str,
        size: Decimal,
        price: Decimal,
        order_value_usd: Decimal,
    ) -> RiskCheckResult:
        """
        Check if the order would exceed position size limits for this symbol.

        Args:
            order_request: Full order request dict
            symbol: Trading pair symbol
            size: Order size in base currency
            price: Order price
            order_value_usd: Order value in USD

        Returns:
            RiskCheckResult
        """
        if symbol not in self.position_limits:
            self.logger.debug(f"No position limit configured for {symbol}, skipping check")
            return RiskCheckResult(passed=True)

        limits = self.position_limits[symbol]
        max_size_usd = limits["max_size_usd"]
        max_leverage = limits["max_leverage"]

        # Get current position value
        current_pos = self.position_manager.get_position(
            order_request.get("exchange_id", "default"), symbol
        )
        current_value = Decimal("0")
        if current_pos and current_pos.side != PositionSide.FLAT:
            current_value = current_pos.size * current_pos.entry_price

        # Calculate new total position value
        new_total_value = current_value + order_value_usd

        # Apply leverage check
        max_position_value = max_size_usd * max_leverage

        if new_total_value > max_position_value:
            return RiskCheckResult(
                passed=False,
                reason=(
                    f"Position size limit exceeded for {symbol}: "
                    f"new total ${new_total_value} > max ${max_position_value} "
                    f"(max_leverage={max_leverage})"
                ),
            )

        self.logger.debug(
            f"Position limit check passed: {symbol} ${new_total_value} <= ${max_position_value}"
        )
        return RiskCheckResult(passed=True)

    async def _check_exposure_limits(
        self,
        order_request: Dict[str, Any],
        exchange_id: str,
        symbol: str,
        order_value_usd: Decimal,
    ) -> RiskCheckResult:
        """
        Check if the order would exceed total or per-exchange exposure limits.

        Args:
            order_request: Full order request dict
            exchange_id: Exchange identifier
            symbol: Trading pair symbol
            order_value_usd: Order value in USD

        Returns:
            RiskCheckResult
        """
        # Calculate total current exposure across all positions
        total_exposure = Decimal("0")
        exchange_exposure = Decimal("0")

        for pos in self.position_manager.get_all_positions():
            pos_value = pos.size * pos.current_price
            total_exposure += pos_value

            if pos.exchange_id == exchange_id:
                exchange_exposure += pos_value

        # Add pending order value
        new_total_exposure = total_exposure + order_value_usd
        new_exchange_exposure = exchange_exposure + order_value_usd

        # Check total exposure
        if new_total_exposure > self.total_max_exposure:
            return RiskCheckResult(
                passed=False,
                reason=(
                    f"Total exposure limit exceeded: "
                    f"new total ${new_total_exposure} > max ${self.total_max_exposure}"
                ),
            )

        # Check per-exchange exposure
        if new_exchange_exposure > self.max_exposure_per_exchange:
            return RiskCheckResult(
                passed=False,
                reason=(
                    f"Per-exchange exposure limit exceeded for {exchange_id}: "
                    f"new ${new_exchange_exposure} > max ${self.max_exposure_per_exchange}"
                ),
            )

        self.logger.debug(
            f"Exposure check passed: total=${new_total_exposure}, "
            f"{exchange_id}=${new_exchange_exposure}"
        )
        return RiskCheckResult(passed=True)

    async def _check_drawdown_limits(
        self,
        order_request: Dict[str, Any],
    ) -> RiskCheckResult:
        """
        Check if current portfolio drawdown exceeds configured limits.

        Args:
            order_request: Full order request dict (unused but kept for interface consistency)

        Returns:
            RiskCheckResult
        """
        total_equity = self.position_manager.get_total_equity()
        initial_capital = self.position_manager.total_capital

        if total_equity >= initial_capital:
            # No drawdown
            return RiskCheckResult(passed=True)

        drawdown = initial_capital - total_equity
        drawdown_percent = drawdown / initial_capital

        if drawdown_percent > self.max_drawdown_percent:
            return RiskCheckResult(
                passed=False,
                reason=(
                    f"Drawdown limit exceeded: {drawdown_percent * 100:.2f}% "
                    f"(max {self.max_drawdown_percent * 100}%) - "
                    f"equity ${total_equity} vs initial ${initial_capital}"
                ),
            )

        self.logger.debug(
            f"Drawdown check passed: {drawdown_percent * 100:.2f}% "
            f"<= {self.max_drawdown_percent * 100}%"
        )
        return RiskCheckResult(passed=True)
