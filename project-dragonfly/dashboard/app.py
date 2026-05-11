"""
Flask + Socket.IO dashboard server for Project Dragonfly.

Provides real-time WebSocket updates for trades, P&L, and positions
using Flask-SocketIO with eventlet for non-blocking operation.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO, emit
from pydantic import BaseModel, Field

from dashboard.charts import format_pnl_for_chart, format_positions_for_chart
from dashboard.trade_logger import TradeLogEntry


class MockTrade(BaseModel):
    """Mock trade model for dashboard development and testing.

    Attributes:
        id: Unique trade identifier.
        strategy: Strategy name that generated the trade.
        symbol: Trading pair symbol.
        side: Trade direction ("buy" or "sell").
        amount: Quantity traded.
        price: Execution price.
        timestamp: ISO format timestamp.
        pnl: Profit/loss from the trade.
    """

    id: str = Field(..., description="Unique trade ID")
    strategy: str = Field(..., description="Strategy name")
    symbol: str = Field(..., description="Trading pair symbol")
    side: str = Field(..., description="Trade direction: buy or sell")
    amount: float = Field(..., description="Quantity traded")
    price: float = Field(..., description="Execution price")
    timestamp: str = Field(..., description="ISO format timestamp")
    pnl: float = Field(default=0.0, description="Profit/loss")


class MockPosition(BaseModel):
    """Mock position model for dashboard development and testing.

    Attributes:
        symbol: Trading pair symbol.
        size: Current position size.
        entry_price: Average entry price.
        current_price: Current market price.
        unrealized_pnl: Unrealized profit/loss.
        timestamp: ISO format timestamp of last update.
    """

    symbol: str = Field(..., description="Trading pair symbol")
    size: float = Field(..., description="Position size")
    entry_price: float = Field(..., description="Average entry price")
    current_price: float = Field(..., description="Current market price")
    unrealized_pnl: float = Field(default=0.0, description="Unrealized P&L")
    timestamp: str = Field(..., description="ISO format timestamp")


class DashboardApp:
    """Real-time trading dashboard with Socket.IO support.

    Manages trade log, positions, and P&L history with WebSocket broadcast
    capabilities for live UI updates.
    """

    def __init__(self, port: int = 5000, debug: bool = False) -> None:
        """Initialize the dashboard application.

        Args:
            port: TCP port to listen on. Defaults to 5000.
            debug: Enable debug mode. Defaults to False.
        """
        self.port = port
        self.debug = debug
        self._logger = logging.getLogger(self.__class__.__name__)

        # Initialize Flask app with template and static folders set to dashboard directory
        self.app = Flask(
            __name__,
            template_folder=".",
            static_folder=".",
        )
        self.app.config["SECRET_KEY"] = "dragonfly-dashboard-secret"

        # Initialize Socket.IO with eventlet for async support
        self.socketio = SocketIO(
            self.app,
            async_mode="eventlet",
            cors_allowed_origins="*",
            logger=debug,
            engineio_logger=debug,
        )

        # Internal state
        self._trade_log: List[MockTrade] = []
        self._current_positions: Dict[str, MockPosition] = {}
        self._pnl_history: List[Dict[str, Any]] = []

        self._setup_routes()
        self._setup_socketio_events()

        self._logger.info("DashboardApp initialized on port %d", port)

    def _setup_routes(self) -> None:
        """Configure HTTP routes for the dashboard."""

        @self.app.route("/")
        def index() -> Any:
            """Serve the main dashboard HTML page."""
            return render_template("index.html")

        @self.app.route("/api/health")
        def health() -> Dict[str, Any]:
            """Health check endpoint."""
            return jsonify({"status": "healthy", "port": self.port})

        @self.app.route("/api/trade_log")
        def get_trade_log() -> Any:
            """Return the full trade log as JSON."""
            return jsonify([trade.model_dump() for trade in self._trade_log])

        @self.app.route("/api/pnl_history")
        def get_pnl_history() -> Any:
            """Return P&L history as JSON."""
            return jsonify(self._pnl_history)

        @self.app.route("/api/positions")
        def get_positions() -> Any:
            """Return current positions as JSON."""
            return jsonify(
                {symbol: pos.model_dump() for symbol, pos in self._current_positions.items()}
            )

        @self.app.route("/api/chart/pnl")
        def get_pnl_chart_data() -> Any:
            """Return formatted P&L data for charts."""
            return jsonify(format_pnl_for_chart(self._pnl_history))

        @self.app.route("/api/chart/positions/<symbol>")
        def get_positions_chart_data(symbol: str) -> Any:
            """Return formatted position data for a symbol."""
            # For now, return mock data - in production, query historical positions
            mock_history = [
                {"timestamp": "2026-04-30T19:00:00Z", "size": 0.01},
                {"timestamp": "2026-04-30T19:05:00Z", "size": 0.015},
                {"timestamp": "2026-04-30T19:10:00Z", "size": 0.008},
            ]
            return jsonify(format_positions_for_chart(mock_history, symbol))

    def _setup_socketio_events(self) -> None:
        """Configure Socket.IO event handlers."""

        @self.socketio.on("connect")
        def handle_connect() -> None:
            """Handle new WebSocket client connection."""
            self._logger.info("Client connected")
            # Send current state to newly connected client
            emit("trade_log_update", [trade.model_dump() for trade in self._trade_log])
            emit(
                "positions_update",
                {symbol: pos.model_dump() for symbol, pos in self._current_positions.items()},
            )
            emit("pnl_update", self._pnl_history)

        @self.socketio.on("disconnect")
        def handle_disconnect() -> None:
            """Handle WebSocket client disconnection."""
            self._logger.info("Client disconnected")

        @self.socketio.on("request_sync")
        def handle_sync_request() -> None:
            """Handle client request for full state sync."""
            emit("trade_log_update", [trade.model_dump() for trade in self._trade_log])
            emit(
                "positions_update",
                {symbol: pos.model_dump() for symbol, pos in self._current_positions.items()},
            )
            emit("pnl_update", self._pnl_history)

    async def emit_trade_update(self, trade: MockTrade) -> None:
        """Broadcast a new trade update to all connected clients.

        Args:
            trade: The trade to broadcast.
        """
        self._trade_log.append(trade)
        self._logger.debug("Emitting trade update: %s", trade.id)
        self.socketio.emit("trade_log_update", [t.model_dump() for t in self._trade_log])

    async def emit_position_update(self, position: MockPosition) -> None:
        """Broadcast a position update to all connected clients.

        Args:
            position: The updated position.
        """
        self._current_positions[position.symbol] = position
        self._logger.debug("Emitting position update: %s", position.symbol)
        self.socketio.emit(
            "positions_update",
            {symbol: pos.model_dump() for symbol, pos in self._current_positions.items()},
        )

    async def emit_pnl_update(self, pnl_entry: Dict[str, Any]) -> None:
        """Broadcast a P&L update to all connected clients.

        Args:
            pnl_entry: P&L entry with 'timestamp' and 'total_pnl' fields.
        """
        self._pnl_history.append(pnl_entry)
        self._logger.debug("Emitting P&L update: %s", pnl_entry)
        self.socketio.emit("pnl_update", self._pnl_history)

    def run(self) -> None:
        """Start the Flask-SocketIO server.

        This method blocks the calling thread and runs the WebSocket server.
        """
        self._logger.info("Starting dashboard server on port %d", self.port)
        self.socketio.run(self.app, host="0.0.0.0", port=self.port, debug=False)


# Default application instance
app: Optional[DashboardApp] = None


def get_app() -> DashboardApp:
    """Get or create the default dashboard application instance."""
    global app
    if app is None:
        app = DashboardApp()
    return app