"""ML-based signal strategy with model integration placeholder."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Signal, SignalType, Strategy

# Optional ONNX Runtime import with fallback
try:
    import onnxruntime as _ort

    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

# Optional sklearn import with fallback
try:
    import sklearn  # noqa: F401

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class MLSignalStrategy(Strategy):
    """ML-based signal strategy that uses a trained model for predictions.

    Supports loading models from pickle files or ONNX format.
    Placeholder for full ML pipeline integration.
    """

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.model_path: Optional[str] = config.get("model_path")
        self.threshold_buy: float = config.get("threshold_buy", 0.6)
        self.threshold_sell: float = config.get("threshold_sell", 0.4)
        self.size_percentage: float = config.get("size_percentage", 0.1)
        self.symbol: str = config.get("symbol", "BTC/USDT")
        self._model: Any = None
        self._feature_names: List[str] = config.get(
            "feature_names",
            ["open", "high", "low", "close", "volume"],
        )
        self._load_model()

    def _load_model(self) -> None:
        """Load ML model from file if path is provided."""
        if self.model_path is None:
            self.logger.warning("No model_path configured, using placeholder mode")
            return

        if not self.model_path.endswith(".onnx"):
            try:
                import pickle

                with open(self.model_path, "rb") as f:
                    self._model = pickle.load(f)
                self.logger.info(f"Loaded pickle model from {self.model_path}")
            except Exception as e:
                self.logger.error(f"Failed to load pickle model: {e}")
        else:
            if not ONNX_AVAILABLE:
                self.logger.error("ONNX Runtime not available, cannot load .onnx model")
                return
            try:
                self._model = _ort.InferenceSession(self.model_path)
                self.logger.info(f"Loaded ONNX model from {self.model_path}")
            except Exception as e:
                self.logger.error(f"Failed to load ONNX model: {e}")

    def validate_config(self) -> bool:
        if self.threshold_buy <= self.threshold_sell:
            self.logger.error("threshold_buy must be greater than threshold_sell")
            return False
        if not (0.0 < self.size_percentage <= 1.0):
            self.logger.error("size_percentage must be in (0, 1]")
            return False
        return True

    def _extract_features(self, data: Dict[str, Any]) -> List[float]:
        """Extract features from market data for model input."""
        features = []
        for fname in self._feature_names:
            val = data.get(fname)
            if val is not None:
                features.append(float(val))
            else:
                features.append(0.0)
        return features

    def _predict(self, features: List[float]) -> float:
        """Run model prediction. Returns probability of upward movement."""
        if self._model is None:
            return 0.5

        if ONNX_AVAILABLE and hasattr(self._model, "run"):
            input_name = self._model.get_inputs()[0].name
            output_name = self._model.get_outputs()[0].name
            result = self._model.run([output_name], {input_name: [features]})
            return float(result[0][0])
        else:
            import numpy as np

            features_arr = np.array([features])
            pred = self._model.predict_proba(features_arr)[0]
            return float(pred[1] if len(pred) > 1 else pred[0])

    async def on_market_data(self, data: Dict[str, Any]) -> Optional[Signal]:
        """Process market data and generate ML-based signals."""
        symbol = data.get("symbol", self.symbol)
        price = data.get("price")

        if price is None:
            self.logger.warning("No price in market data")
            return None

        features = self._extract_features(data)
        probability = self._predict(features)

        signal_type: Optional[SignalType] = None
        if probability >= self.threshold_buy:
            signal_type = SignalType.BUY
        elif probability <= self.threshold_sell:
            signal_type = SignalType.SELL

        if signal_type is None:
            return None

        self.logger.info(
            f"ML signal: {signal_type.value} (prob={probability:.3f}) at price={price}"
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
                float(price) * 1.04 if signal_type == SignalType.BUY
                else float(price) * 0.96
            ),
        )

    async def on_order_update(self, order_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Order update: {order_update}")

    async def on_position_update(self, position_update: Dict[str, Any]) -> None:
        self.logger.debug(f"Position update: {position_update}")

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "threshold_buy": self.threshold_buy,
            "threshold_sell": self.threshold_sell,
            "size_percentage": self.size_percentage,
            "model_loaded": self._model is not None,
            "model_path": self.model_path,
        }