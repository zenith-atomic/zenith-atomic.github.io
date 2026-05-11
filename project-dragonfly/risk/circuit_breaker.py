"""Circuit breaker for emergency stop mechanisms."""
from typing import Dict, Any, Optional
import logging
import asyncio
import time
from collections import deque
from decimal import Decimal

from .position_manager import PositionManager


class CircuitBreaker:
    """
    Implements emergency stop mechanisms for the trading system.

    Monitors:
    - Market volatility (rapid price movements)
    - Exchange connectivity
    - Unhandled exceptions (error rate)
    - Trade volume anomalies

    When any condition trips the breaker, trading is halted until reset.
    """

    def __init__(self, config: Dict[str, Any], position_manager: Optional[PositionManager] = None):
        """
        Initialize circuit breaker with configuration.

        Args:
            config: Circuit breaker configuration dict
            position_manager: Optional PositionManager for equity checks
        """
        self.config = config
        self.position_manager = position_manager
        self.is_tripped = False
        self.trip_reason: Optional[str] = None
        self.trip_timestamp: float = 0.0

        # Load thresholds
        cb_cfg = config.get("circuit_breakers", {})
        self.market_volatility_threshold = Decimal(
            str(cb_cfg.get("market_volatility_threshold", 0.05))
        )
        self.exchange_disconnect_threshold_sec = cb_cfg.get(
            "exchange_disconnect_threshold_sec", 300
        )
        self.unhandled_exception_count_threshold = cb_cfg.get(
            "unhandled_exception_count", 5
        )
        self.trade_volume_anomaly_factor = Decimal(
            str(cb_cfg.get("trade_volume_anomaly_factor", 3.0))
        )

        # State tracking
        self._exception_timestamps: deque = deque(maxlen=100)
        self._recent_prices: Dict[str, deque] = {}  # symbol -> price deque
        self._recent_volumes: deque = deque(maxlen=50)
        self._lock = asyncio.Lock()

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(
            f"CircuitBreaker initialized: volatility={self.market_volatility_threshold}, "
            f"disconnect_timeout={self.exchange_disconnect_threshold_sec}s, "
            f"exception_thresh={self.unhandled_exception_count_threshold}, "
            f"volume_anomaly={self.trade_volume_anomaly_factor}x"
        )

    async def check(
        self,
        current_market_conditions: Dict[str, Any],
        system_health: Dict[str, Any],
    ) -> bool:
        """
        Check various conditions to determine if the circuit breaker should trip.

        Args:
            current_market_conditions: Dict with keys like:
                - prices: Dict[str, float] - current prices by symbol
                - volumes: Dict[str, float] - volumes by symbol
                - exchange_status: Dict[str, bool] - connectivity by exchange
                - timestamp: float
            system_health: Dict with keys like:
                - exception_count_1h: int
                - last_exception_time: float
                - is_connected: bool
                - latency_ms: float

        Returns:
            True if circuit breaker is now tripped (was already or just tripped)
        """
        async with self._lock:
            if self.is_tripped:
                return True

            reasons = []

            # Check market volatility
            vol_reason = await self._check_volatility(current_market_conditions)
            if vol_reason:
                reasons.append(vol_reason)

            # Check exchange connectivity
            conn_reason = await self._check_connectivity(current_market_conditions, system_health)
            if conn_reason:
                reasons.append(conn_reason)

            # Check exception rate
            exc_reason = self._check_exception_rate(system_health)
            if exc_reason:
                reasons.append(exc_reason)

            # Check trade volume anomaly
            vol_anom_reason = await self._check_volume_anomaly(current_market_conditions)
            if vol_anom_reason:
                reasons.append(vol_anom_reason)

            if reasons:
                combined_reason = " | ".join(reasons)
                self._trip(combined_reason)
                return True

            return False

    async def _check_volatility(
        self,
        market_conditions: Dict[str, Any],
    ) -> Optional[str]:
        """
        Check if market volatility exceeds threshold.

        Compares current price to recent prices and flags large % moves.
        """
        prices = market_conditions.get("prices", {})
        timestamp = market_conditions.get("timestamp", time.time())

        for symbol, current_price in prices.items():
            price_dec = Decimal(str(current_price))

            if symbol not in self._recent_prices:
                self._recent_prices[symbol] = deque(maxlen=10)

            # Store price with timestamp
            self._recent_prices[symbol].append((price_dec, timestamp))

            # Need at least 2 prices to compute move
            if len(self._recent_prices[symbol]) < 2:
                continue

            prices_list = list(self._recent_prices[symbol])
            prev_price, prev_time = prices_list[-2]

            if prev_price <= 0:
                continue

            price_change_pct = abs(price_dec - prev_price) / prev_price

            if price_change_pct > self.market_volatility_threshold:
                time_diff = timestamp - prev_time
                return (
                    f"High volatility: {symbol} moved {price_change_pct * 100:.2f}% "
                    f"in {time_diff:.1f}s (threshold: {self.market_volatility_threshold * 100}%)"
                )

        return None

    async def _check_connectivity(
        self,
        market_conditions: Dict[str, Any],
        system_health: Dict[str, Any],
    ) -> Optional[str]:
        """
        Check if any exchange is disconnected or latency is too high.
        """
        # Check exchange status from market conditions
        exchange_status = market_conditions.get("exchange_status", {})

        for exchange_id, is_connected in exchange_status.items():
            if not is_connected:
                last_heartbeat = market_conditions.get("last_heartbeat", {}).get(exchange_id, 0)
                time_since_heartbeat = time.time() - last_heartbeat

                if time_since_heartbeat > self.exchange_disconnect_threshold_sec:
                    return (
                        f"Exchange {exchange_id} disconnected for "
                        f"{time_since_heartbeat:.0f}s (threshold: {self.exchange_disconnect_threshold_sec}s)"
                    )

        # Check system health connectivity
        if not system_health.get("is_connected", True):
            return "System health: not connected"

        # Check latency
        latency_ms = system_health.get("latency_ms", 0)
        if latency_ms > 5000:  # 5 second latency
            return f"High latency: {latency_ms}ms"

        return None

    def _check_exception_rate(self, system_health: Dict[str, Any]) -> Optional[str]:
        """
        Check if exception rate in the last hour exceeds threshold.
        """
        exception_count = system_health.get("exception_count_1h", 0)

        if exception_count >= self.unhandled_exception_count_threshold:
            return (
                f"High exception rate: {exception_count} in last hour "
                f"(threshold: {self.unhandled_exception_count_threshold})"
            )

        return None

    async def _check_volume_anomaly(
        self,
        market_conditions: Dict[str, Any],
    ) -> Optional[str]:
        """
        Check if trading volume is abnormally high compared to average.
        """
        volumes = market_conditions.get("volumes", {})

        # Update recent volumes
        for symbol, volume in volumes.items():
            try:
                vol_float = float(volume)
                self._recent_volumes.append(vol_float)
            except (ValueError, TypeError):
                pass

        # Need enough data points
        if len(self._recent_volumes) < 10:
            return None

        # Calculate average and std dev
        import statistics
        volumes_list = list(self._recent_volumes)
        avg_volume = statistics.mean(volumes_list)
        if avg_volume <= 0:
            return None

        try:
            std_dev = statistics.stdev(volumes_list)
        except statistics.StatisticsError:
            std_dev = 0

        # Check latest volume
        if not volumes_list:
            return None

        latest_volume = volumes_list[-1]
        if latest_volume > avg_volume + (std_dev * float(self.trade_volume_anomaly_factor)):
            return (
                f"Volume anomaly: latest volume {latest_volume:.2f} "
                f"exceeds {self.trade_volume_anomaly_factor}x avg ({avg_volume:.2f})"
            )

        return None

    def trip(self, reason: str) -> None:
        """
        Manually trip the circuit breaker.

        Args:
            reason: Why the breaker was tripped
        """
        self._trip(reason)

    def _trip(self, reason: str) -> None:
        """Internal trip logic."""
        self.is_tripped = True
        self.trip_reason = reason
        self.trip_timestamp = time.time()
        self.logger.critical(
            f"CIRCUIT BREAKER TRIPPED: {reason} at {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(self.trip_timestamp))}"
        )

    def reset(self) -> None:
        """
        Reset the circuit breaker after the issue has been resolved.

        Should only be called after manual review or automatic cool-off period.
        """
        if self.is_tripped:
            self.logger.warning(
                f"Circuit breaker reset. Was tripped for: {self.trip_reason} "
                f"({time.time() - self.trip_timestamp:.1f}s ago)"
            )
        self.is_tripped = False
        self.trip_reason = None
        self.trip_timestamp = 0.0

    def is_active(self) -> bool:
        """
        Check if the circuit breaker is currently active (tripped).

        Returns:
            True if tripped/blocking trades
        """
        return self.is_tripped

    def record_exception(self) -> None:
        """
        Record an unhandled exception for rate tracking.
        Call this when catching unexpected exceptions.
        """
        self._exception_timestamps.append(time.time())

    def get_status(self) -> Dict[str, Any]:
        """
        Get current circuit breaker status.

        Returns:
            Dict with tripped state, reason, and stats
        """
        # Clean old exceptions (>1 hour)
        now = time.time()
        cutoff = now - 3600
        while self._exception_timestamps and self._exception_timestamps[0] < cutoff:
            self._exception_timestamps.popleft()

        return {
            "is_tripped": self.is_tripped,
            "trip_reason": self.trip_reason,
            "trip_timestamp": self.trip_timestamp,
            "exception_count_1h": len(self._exception_timestamps),
            "exception_threshold": self.unhandled_exception_count_threshold,
        }
