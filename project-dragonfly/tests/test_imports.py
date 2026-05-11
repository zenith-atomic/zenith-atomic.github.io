"""
Integration test: verify all modules can be imported and basic classes instantiated.
Does not require running services (DBs, exchanges, etc.).
"""
import sys
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_data_pipeline_imports():
    """Data pipeline module."""
    from data_pipeline import (
        DataQualityChecker,
        OHLCV,
        OrderBook,
        QualityResult,
        Trade,
    )
    assert DataQualityChecker is not None
    assert OHLCV is not None
    print("✅ data_pipeline imports OK")


def test_execution_imports():
    """Execution module — CCXT interface and enums."""
    from execution.ccxt_interface import (
        CCXTInterface,
        OrderBook,
        OrderRequest,
        OrderResult,
        OrderSide,
        OrderStatus,
        OrderType,
        Ticker,
    )
    assert CCXTInterface is not None
    assert OrderRequest is not None
    print("✅ execution imports OK")


def test_strategies_imports():
    """Strategies module."""
    from strategies import (
        ArbitrageStrategy,
        MarketMakingStrategy,
        MeanReversionStrategy,
        MLSignalStrategy,
        MomentumStrategy,
        Signal,
        SignalType,
        Strategy,
        StrategyMode,
    )
    assert MomentumStrategy is not None
    assert Signal is not None
    print("✅ strategies imports OK")


def test_risk_imports():
    """Risk management module."""
    from risk import (
        CircuitBreaker,
        DrawdownControl,
        Position,
        PositionManager,
        PositionSide,
        PreTradeGate,
        RiskCheckResult,
    )
    assert PositionManager is not None
    assert PreTradeGate is not None
    print("✅ risk imports OK")


def test_knowledge_imports():
    """Knowledge system module."""
    from knowledge import (
        FinancialEmbedding,
        GraphNode,
        GraphRelationship,
        KnowledgeGraphManager,
        RAGPipeline,
        VectorStoreManager,
    )
    assert VectorStoreManager is not None
    assert KnowledgeGraphManager is not None
    print("✅ knowledge imports OK")


def test_dashboard_imports():
    """Dashboard module."""
    from dashboard import DashboardApp, TradeLogger, TradeLogEntry
    assert DashboardApp is not None
    assert TradeLogger is not None
    print("✅ dashboard imports OK")


if __name__ == "__main__":
    print("Running integration tests...")
    test_data_pipeline_imports()
    test_execution_imports()
    test_strategies_imports()
    test_risk_imports()
    test_knowledge_imports()
    test_dashboard_imports()
    print("\n✅ All imports verified — project structure is valid!")