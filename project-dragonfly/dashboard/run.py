#!/usr/bin/env python3
"""
Dashboard entry point for Project Dragonfly.

Starts the Flask-SocketIO dashboard server with mock data simulation
for development and testing purposes.
"""

from __future__ import annotations

import sys
sys.path.insert(0, "/app")

# Must be before other imports
import eventlet
eventlet.monkey_patch()

import asyncio
import logging
import signal
import sys
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from dashboard.app import DashboardApp, MockPosition, MockTrade


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DashboardRunner:
    """Manages the dashboard application lifecycle with mock data simulation."""

    def __init__(self, port: int = 5000) -> None:
        """Initialize the dashboard runner.

        Args:
            port: TCP port for the dashboard server.
        """
        self.port = port
        self.dashboard: Optional[DashboardApp] = None
        self._shutdown_event: Optional[asyncio.Event] = None

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully."""
        logger.info("Received signal %d, initiating shutdown...", signum)
        if self._shutdown_event:
            self._shutdown_event.set()

    async def simulate_updates(self) -> None:
        """Simulate real-time trading updates for demonstration."""
        await asyncio.sleep(1)

        # Trade 1: BTC buy (momentum)
        await self.dashboard.emit_trade_update(
            MockTrade(
                id="T001",
                strategy="Momentum",
                symbol="BTC/USDT",
                side="buy",
                amount=0.0100,
                price=69850.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                pnl=0.0,
            )
        )
        logger.info("Emitted trade T001 — BTC buy @ 69850")

        # Position 1: BTC long
        await self.dashboard.emit_position_update(
            MockPosition(
                symbol="BTC/USDT",
                size=0.0100,
                entry_price=69850.0,
                current_price=70050.0,
                unrealized_pnl=20.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        logger.info("Emitted position BTC/USDT long")

        await asyncio.sleep(2)

        # Trade 2: ETH sell (arbitrage)
        await self.dashboard.emit_trade_update(
            MockTrade(
                id="T002",
                strategy="Arbitrage",
                symbol="ETH/USDT",
                side="sell",
                amount=0.1500,
                price=3045.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                pnl=0.0,
            )
        )
        logger.info("Emitted trade T002 — ETH sell @ 3045")

        await asyncio.sleep(1)

        # Trade 3: BTC buy (momentum again)
        await self.dashboard.emit_trade_update(
            MockTrade(
                id="T003",
                strategy="Momentum",
                symbol="BTC/USDT",
                side="buy",
                amount=0.0050,
                price=70000.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                pnl=0.0,
            )
        )
        logger.info("Emitted trade T003 — BTC buy @ 70000")

        await asyncio.sleep(2)

        # Trade 4: ETH buy (mean reversion)
        await self.dashboard.emit_trade_update(
            MockTrade(
                id="T004",
                strategy="MeanReversion",
                symbol="ETH/USDT",
                side="buy",
                amount=0.2000,
                price=2980.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                pnl=0.0,
            )
        )
        logger.info("Emitted trade T004 — ETH buy @ 2980")

        # Position 2: ETH
        await self.dashboard.emit_position_update(
            MockPosition(
                symbol="ETH/USDT",
                size=0.2000,
                entry_price=2980.0,
                current_price=2995.0,
                unrealized_pnl=30.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        logger.info("Emitted position ETH/USDT")

        await asyncio.sleep(1)

        # Trade 5: BTC sell (take profit)
        await self.dashboard.emit_trade_update(
            MockTrade(
                id="T005",
                strategy="Momentum",
                symbol="BTC/USDT",
                side="sell",
                amount=0.0050,
                price=70500.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                pnl=25.0,
            )
        )
        logger.info("Emitted trade T005 — BTC sell @ 70500 (+$25)")

        # P&L update
        await self.dashboard.emit_pnl_update({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_pnl": 25.0,
        })
        logger.info("Emitted P&L update")

        await asyncio.sleep(2)

        # Update BTC position after partial sell
        await self.dashboard.emit_position_update(
            MockPosition(
                symbol="BTC/USDT",
                size=0.0050,
                entry_price=69850.0,
                current_price=70500.0,
                unrealized_pnl=32.5,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

        await asyncio.sleep(2)

        # Trade 6: ETH sell (close position)
        await self.dashboard.emit_trade_update(
            MockTrade(
                id="T006",
                strategy="Arbitrage",
                symbol="ETH/USDT",
                side="sell",
                amount=0.2000,
                price=3010.0,
                timestamp=datetime.now(timezone.utc).isoformat(),
                pnl=60.0,
            )
        )
        logger.info("Emitted trade T006 — ETH sell @ 3010 (+$60)")

        # Final P&L update
        await self.dashboard.emit_pnl_update({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_pnl": 85.0,
        })
        logger.info("Emitted final P&L: $85.00")

    async def run_async(self) -> None:
        """Run the dashboard with async simulation."""
        logger.info("Starting DashboardRunner on port %d", self.port)

        self.dashboard = DashboardApp(port=self.port, debug=True)
        self._shutdown_event = asyncio.Event()

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Run simulation in background
        simulation_task = asyncio.create_task(self.simulate_updates())

        # Run the Flask server in a thread to avoid blocking
        import threading
        server_thread = threading.Thread(target=self.dashboard.run, daemon=True)
        server_thread.start()
        logger.info("Dashboard server started in background thread")

        # Wait for shutdown signal
        try:
            await self._shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            simulation_task.cancel()
            try:
                await simulation_task
            except asyncio.CancelledError:
                pass

        logger.info("DashboardRunner shut down complete")

    def run(self) -> None:
        """Entry point for running the dashboard."""
        try:
            asyncio.run(self.run_async())
        except OSError as e:
            if e.errno == 98:
                logger.error("Port %d is already in use. Is the dashboard already running?", self.port)
                sys.exit(1)
            raise


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Project Dragonfly Dashboard")
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port to run the dashboard on (default: 5000)",
    )
    args = parser.parse_args()

    runner = DashboardRunner(port=args.port)
    runner.run()


if __name__ == "__main__":
    main()