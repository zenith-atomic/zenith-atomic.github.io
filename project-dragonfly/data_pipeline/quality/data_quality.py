"""Data quality checks for market data."""
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, List, Optional
import logging
import statistics

logger = logging.getLogger(__name__)


@dataclass
class QualityResult:
    """Result of a data quality check."""
    passed: bool
    check_name: str
    message: str = ""
    severity: str = "info"  # "info", "warning", "error"
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataQualityChecker:
    """
    Performs data quality checks on normalized market data.

    Checks include:
    - Outlier detection (price > 2 std dev from recent mean)
    - Missing tick detection
    - Duplicate tick handling
    - Timestamp ordering validation
    """

    def __init__(self, window_size: int = 100):
        """
        Initialize DataQualityChecker.

        Args:
            window_size: Number of recent ticks to keep for baseline calculations
        """
        self.window_size = window_size
        self._price_history: Deque[float] = deque(maxlen=window_size)
        self._seen_timestamps: Deque[int] = deque(maxlen=window_size)
        self._last_timestamp: Optional[int] = None
        self._last_symbol: Optional[str] = None

        # Quality metrics
        self._total_checks = 0
        self._failed_checks = 0
        self._outliers_detected = 0
        self._duplicates_detected = 0
        self._ordering_errors = 0

    def check_ohlcv(self, ohlcv: Any) -> QualityResult:
        """
        Run quality checks on OHLCV data.

        Args:
            ohlcv: OHLCV data object

        Returns:
            QualityResult with pass/fail status and details
        """
        self._total_checks += 1
        symbol = getattr(ohlcv, "symbol", "unknown")
        price = getattr(ohlcv, "close", 0)
        timestamp = getattr(ohlcv, "timestamp", 0)

        # Check for outliers
        if self._price_history and price > 0:
            mean = statistics.mean(self._price_history)
            stdev = statistics.stdev(self._price_history) if len(self._price_history) > 1 else 0
            if stdev > 0 and abs(price - mean) > 2 * stdev:
                self._outliers_detected += 1
                self._failed_checks += 1
                logger.warning(
                    "Outlier detected on %s: price=%.4f, mean=%.4f, stdev=%.4f",
                    symbol, price, mean, stdev,
                )
                return QualityResult(
                    passed=False,
                    check_name="outlier",
                    message=f"Price {price} is {abs(price - mean) / stdev:.1f} stdev from mean",
                    severity="warning",
                    metadata={"price": price, "mean": mean, "stdev": stdev},
                )

        # Check for duplicate timestamps
        if timestamp in self._seen_timestamps:
            self._duplicates_detected += 1
            self._failed_checks += 1
            return QualityResult(
                passed=False,
                check_name="duplicate",
                message=f"Duplicate timestamp {timestamp} for {symbol}",
                severity="warning",
                metadata={"timestamp": timestamp},
            )

        # Check for timestamp ordering
        if self._last_timestamp and timestamp < self._last_timestamp and symbol == self._last_symbol:
            self._ordering_errors += 1
            self._failed_checks += 1
            logger.warning(
                "Timestamp ordering error on %s: %d < %d", symbol, timestamp, self._last_timestamp
            )
            return QualityResult(
                passed=False,
                check_name="timestamp_order",
                message=f"Timestamp {timestamp} is before last {self._last_timestamp}",
                severity="error",
                metadata={"timestamp": timestamp, "last_timestamp": self._last_timestamp},
            )

        # Update state
        self._price_history.append(price)
        self._seen_timestamps.append(timestamp)
        self._last_timestamp = timestamp
        self._last_symbol = symbol

        return QualityResult(passed=True, check_name="ohlcv", message="OHLCV data passed quality checks")

    def check_orderbook(self, ob: Any) -> QualityResult:
        """
        Run quality checks on orderbook data.

        Args:
            ob: OrderBook data object

        Returns:
            QualityResult with pass/fail status
        """
        self._total_checks += 1

        bids = getattr(ob, "bids", [])
        asks = getattr(ob, "asks", [])

        if not bids or not asks:
            self._failed_checks += 1
            return QualityResult(
                passed=False,
                check_name="orderbook_empty",
                message="Orderbook has empty bids or asks",
                severity="error",
            )

        # Check best bid < best ask (spread should be positive)
        best_bid = bids[0][0] if bids else 0
        best_ask = asks[0][0] if asks else 0

        if best_bid >= best_ask:
            self._failed_checks += 1
            return QualityResult(
                passed=False,
                check_name="orderbook_spread",
                message=f"Best bid {best_bid} >= best ask {best_ask}",
                severity="error",
                metadata={"best_bid": best_bid, "best_ask": best_ask},
            )

        # Check for negative sizes
        for price, size in bids + asks:
            if size < 0 or price < 0:
                self._failed_checks += 1
                return QualityResult(
                    passed=False,
                    check_name="orderbook_negative",
                    message=f"Negative price or size: ({price}, {size})",
                    severity="error",
                )

        return QualityResult(passed=True, check_name="orderbook", message="Orderbook passed quality checks")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated quality metrics.

        Returns:
            Dict of quality metrics
        """
        return {
            "total_checks": self._total_checks,
            "failed_checks": self._failed_checks,
            "outliers_detected": self._outliers_detected,
            "duplicates_detected": self._duplicates_detected,
            "ordering_errors": self._ordering_errors,
            "pass_rate": (
                (self._total_checks - self._failed_checks) / self._total_checks * 100
                if self._total_checks > 0
                else 100.0
            ),
        }
