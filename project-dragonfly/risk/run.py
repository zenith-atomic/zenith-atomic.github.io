"""
Test entry point for the risk management layer.

Demonstrates:
- Loading risk configuration
- Initializing PositionManager, PreTradeGate, DrawdownControl
- Simulating trades and market data updates
- Running risk checks
- Monitoring drawdown
"""
import asyncio
import logging
import sys
import time
from decimal import Decimal
from pathlib import Path

import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from risk import (
    PositionManager,
    PositionSide,
    PreTradeGate,
    DrawdownControl,
    CircuitBreaker,
    RiskCheckResult,
)


def setup_logging():
    """Configure logging for the test run."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config(config_path: str) -> dict:
    """Load risk configuration from YAML file."""
    with open(config_path, "r") as f:
        full_config = yaml.safe_load(f)
    return full_config.get("risk_management", {})


async def run_demo():
    """Run the demonstration of the risk management system."""
    logger = logging.getLogger("risk_demo")
    logger.info("=" * 60)
    logger.info("Project Dragonfly - Risk Management Demo")
    logger.info("=" * 60)

    # Load configuration
    config_path = Path(__file__).parent.parent / "configs" / "risk.yaml"
    config = load_config(str(config_path))
    logger.info(f"Loaded config from {config_path}")
    logger.info(f"Initial capital: ${config['initial_capital']}")

    # Initialize PositionManager
    initial_capital = Decimal(str(config["initial_capital"]))
    pm = PositionManager(initial_capital=initial_capital)
    logger.info(f"PositionManager created with capital: ${pm.total_capital}")

    # Initialize PreTradeGate
    gate = PreTradeGate(config, pm)
    logger.info("PreTradeGate initialized")

    # Initialize DrawdownControl
    drawdown_control = DrawdownControl(config["drawdown_control"], pm)
    logger.info("DrawdownControl initialized")

    # Initialize CircuitBreaker
    cb = CircuitBreaker(config, pm)
    logger.info("CircuitBreaker initialized")

    logger.info("")
    logger.info("-" * 60)
    logger.info("SCENARIO 1: Opening a BTC/USDT long position")
    logger.info("-" * 60)

    # Simulate opening a BTC position
    btc_trade = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "size": "0.5",  # 0.5 BTC
        "price": "65000",
    }
    logger.info(f"Trade: {btc_trade}")
    await pm.handle_trade(btc_trade)

    # Run pre-trade checks
    order_request = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "size": Decimal("0.5"),
        "price": Decimal("65000"),
    }
    result = await gate.run_checks(order_request)
    logger.info(f"Pre-trade check result: passed={result.passed}, reason={result.reason}")

    # Update market data (price moves up)
    await pm.handle_market_data({"symbol": "BTC/USDT", "price": "67000"})
    logger.info(f"Total equity after BTC up: ${pm.get_total_equity()}")
    logger.info(f"Unrealized P&L: ${pm.get_total_unrealized_pnl()}")

    # Update drawdown
    await drawdown_control.update_equity()
    logger.info(f"Drawdown: {drawdown_control.get_current_drawdown() * 100:.2f}%")
    logger.info(f"Drawdown status: {drawdown_control.get_status()}")

    logger.info("")
    logger.info("-" * 60)
    logger.info("SCENARIO 2: Opening an ETH/USDT position")
    logger.info("-" * 60)

    eth_trade = {
        "exchange_id": "binance",
        "symbol": "ETH/USDT",
        "side": "buy",
        "size": "5",  # 5 ETH
        "price": "3500",
    }
    logger.info(f"Trade: {eth_trade}")
    await pm.handle_trade(eth_trade)

    # Check all positions
    logger.info("")
    logger.info("All open positions:")
    for pos in pm.get_all_positions():
        logger.info(
            f"  {pos.exchange_id}:{pos.symbol} | {pos.side.value} | "
            f"size={pos.size} | entry={pos.entry_price} | current={pos.current_price} | "
            f"unrealized_pnl={pos.unrealized_pnl}"
        )

    # Update drawdown
    await drawdown_control.update_equity()
    logger.info(f"Drawdown after ETH: {drawdown_control.get_current_drawdown() * 100:.2f}%")

    logger.info("")
    logger.info("-" * 60)
    logger.info("SCENARIO 3: Testing position limit check (should fail)")
    logger.info("-" * 60)

    # Try to open a very large BTC position (should fail limit check)
    large_order = {
        "exchange_id": "binance",
        "symbol": "BTC/USDT",
        "side": "buy",
        "size": Decimal("1.0"),  # 1 BTC at $65k = $65k, exceeds $10k limit
        "price": Decimal("65000"),
    }
    result = await gate.run_checks(large_order)
    logger.info(f"Large order check: passed={result.passed}")
    if not result.passed:
        logger.info(f"  Blocked as expected: {result.reason}")

    logger.info("")
    logger.info("-" * 60)
    logger.info("SCENARIO 4: Simulating market crash (drawdown breach)")
    logger.info("-" * 60)

    # Simulate BTC crashing 25%
    logger.info("BTC drops from $67k to $48k (-25%)")
    await pm.handle_market_data({"symbol": "BTC/USDT", "price": "48000"})

    # Update drawdown
    await drawdown_control.update_equity()
    logger.info(f"Drawdown after crash: {drawdown_control.get_current_drawdown() * 100:.2f}%")
    logger.info(f"Drawdown breach active: {drawdown_control.is_drawdown_breached()}")
    logger.info(f"Drawdown status: {drawdown_control.get_status()}")

    # Try to trade while in breach
    small_order = {
        "exchange_id": "binance",
        "symbol": "ETH/USDT",
        "side": "buy",
        "size": Decimal("0.1"),
        "price": Decimal("3500"),
    }
    result = await gate.run_checks(small_order)
    logger.info(f"Trade during breach check: passed={result.passed}")
    if not result.passed:
        logger.info(f"  Blocked: {result.reason}")

    logger.info("")
    logger.info("-" * 60)
    logger.info("SCENARIO 5: Circuit breaker - high volatility")
    logger.info("-" * 60)

    # Simulate a price spike
    market_conditions = {
        "prices": {"BTC/USDT": 90000},  # Huge jump
        "timestamp": time.time(),
        "exchange_status": {"binance": True},
        "volumes": {"BTC/USDT": 1000},
    }
    system_health = {
        "exception_count_1h": 1,
        "is_connected": True,
        "latency_ms": 50,
    }

    is_tripped = await cb.check(market_conditions, system_health)
    logger.info(f"Circuit breaker tripped: {cb.is_active()}")
    if cb.is_active():
        logger.info(f"  Reason: {cb.trip_reason}")

    logger.info("")
    logger.info("-" * 60)
    logger.info("SCENARIO 6: Closing a position")
    logger.info("-" * 60)

    # Close the ETH position
    closed_pos = await pm.close_position("binance", "ETH/USDT", Decimal("3400"))
    logger.info(f"Closed ETH position: realized_pnl={closed_pos.realized_pnl}")
    logger.info(f"Total capital after close: ${pm.total_capital}")
    logger.info(f"Available capital: ${pm.get_available_capital()}")

    logger.info("")
    logger.info("-" * 60)
    logger.info("FINAL STATUS")
    logger.info("-" * 60)
    logger.info(f"Total equity: ${pm.get_total_equity()}")
    logger.info(f"Total unrealized P&L: ${pm.get_total_unrealized_pnl()}")
    logger.info(f"Total realized P&L: ${pm.get_total_realized_pnl()}")
    logger.info(f"Drawdown: {drawdown_control.get_current_drawdown() * 100:.2f}%")
    logger.info(f"Drawdown breached: {drawdown_control.is_drawdown_breached()}")
    logger.info(f"Circuit breaker active: {cb.is_active()}")
    logger.info(f"Circuit breaker status: {cb.get_status()}")
    logger.info("")
    logger.info("Remaining positions:")
    for pos in pm.get_all_positions():
        logger.info(
            f"  {pos.exchange_id}:{pos.symbol} | {pos.side.value} | "
            f"size={pos.size} | unrealized_pnl={pos.unrealized_pnl}"
        )

    logger.info("")
    logger.info("=" * 60)
    logger.info("Demo completed successfully!")
    logger.info("=" * 60)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(run_demo())
