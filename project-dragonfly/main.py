"""
Dragonfly Trading Bot — Main Orchestrator
Wires together all components: data pipeline, execution, strategies, risk, knowledge.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

# Ensure project root is in path so all modules resolve
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def _load_config(config_dir: Path, filename: str) -> dict:
    """Load a YAML config file, returning empty dict if missing."""
    path = config_dir / filename
    if path.exists():
        with open(path) as f:
            return yaml.safe_load(f) or {}
    return {}


async def main() -> None:
    """Main entry point for the Dragonfly trading bot."""
    config_dir = PROJECT_ROOT / "configs"

    # Load all configs
    data_config = _load_config(config_dir, "data_pipeline.yaml")
    execution_config = _load_config(config_dir, "execution.yaml")
    strategies_config = _load_config(config_dir, "strategies.yaml")
    risk_config = _load_config(config_dir, "risk.yaml")
    knowledge_config = _load_config(config_dir, "knowledge.yaml")

    logger = logging.getLogger("dragonfly.main")
    logger.info("Starting Dragonfly Trading Bot...")

    # ── Data Pipeline ─────────────────────────────────────────────
    try:
        from data_pipeline import (
            MarketDataPipeline,
            QuestDBWriter,
            ClickHouseWriter,
            NATSFeedsManager,
        )
        logger.info("✓ data_pipeline module loaded")
    except ImportError as exc:
        logger.warning(f"data_pipeline not fully available: {exc}")

    # ── Execution ─────────────────────────────────────────────────
    try:
        from execution.ccxt_interface import (
            CCXTInterface,
            OrderManager,
            ExchangeCredentials,
            OrderRequest,
            OrderResult,
        )
        logger.info("✓ execution module loaded")
    except ImportError as exc:
        logger.warning(f"execution not fully available: {exc}")

    # ── Strategies ───────────────────────────────────────────────
    try:
        from strategies import (
            Strategy,
            StrategyMode,
            SignalType,
            Signal,
            MomentumStrategy,
            ArbitrageStrategy,
            MarketMakingStrategy,
            MeanReversionStrategy,
            MLSignalStrategy,
        )
        logger.info("✓ strategies module loaded")
    except ImportError as exc:
        logger.warning(f"strategies not fully available: {exc}")

    # ── Risk ───────────────────────────────────────────────────────
    try:
        from risk import (
            PositionManager,
            PreTradeGate,
            DrawdownControl,
            CircuitBreaker,
            PositionSide,
            Position,
            RiskCheckResult,
        )
        logger.info("✓ risk module loaded")
    except ImportError as exc:
        logger.warning(f"risk not fully available: {exc}")

    # ── Knowledge ─────────────────────────────────────────────────
    try:
        from knowledge import (
            VectorStoreManager,
            KnowledgeGraphManager,
            RAGPipeline,
            FinancialEmbedding,
        )
        logger.info("✓ knowledge module loaded")
    except ImportError as exc:
        logger.warning(f"knowledge not fully available: {exc}")

    # ── Dashboard ─────────────────────────────────────────────────
    try:
        from dashboard import DashboardApp, TradeLogger
        logger.info("✓ dashboard module loaded")
    except ImportError as exc:
        logger.warning(f"dashboard not fully available: {exc}")

    # Log configuration summary
    strategies_raw = strategies_config.get("strategies", {})
    if isinstance(strategies_raw, list):
        strategy_names = [s.get("name", "unknown") if isinstance(s, dict) else str(s) for s in strategies_raw]
    else:
        strategy_names = list(strategies_raw.keys())
    max_drawdown = risk_config.get("risk_management", {}).get("drawdown_control", {}).get("max_drawdown_percent")
    mode = execution_config.get("execution", {}).get("mode", "paper")

    logger.info(f"Configured strategies: {strategy_names}")
    logger.info(f"Max drawdown: {max_drawdown}%")
    logger.info(f"Execution mode: {mode}")
    logger.info("Paper trading mode — no real orders will be placed.")
    logger.info("Dragonfly startup complete.")


def _handle_signal(signum: int, frame, logger: logging.Logger) -> None:
    logger.info(f"Received signal {signum}, shutting down gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    # Graceful shutdown on SIGINT / SIGTERM
    main_logger = logging.getLogger("dragonfly.main")
    signal.signal(signal.SIGINT, lambda s, f: _handle_signal(s, f, main_logger))
    signal.signal(signal.SIGTERM, lambda s, f: _handle_signal(s, f, main_logger))

async def run_main():
    await main()
    # Keep running in paper mode
    while True:
        await asyncio.sleep(60)

asyncio.run(run_main())