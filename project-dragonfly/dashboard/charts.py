"""
Chart data formatting utilities for Project Dragonfly dashboard.

Provides helper functions to format trading data for Chart.js visualization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


def format_pnl_for_chart(pnl_history: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
    """Format P&L history for Chart.js time-series line chart.

    Args:
        pnl_history: List of P&L entries with 'timestamp' and 'total_pnl' fields.

    Returns:
        Dictionary with 'labels' (ISO timestamps) and 'data' (P&L values).
    """
    if not pnl_history:
        return {"labels": [], "data": []}

    df = pd.DataFrame(pnl_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return {
        "labels": df["timestamp"].dt.isoformat().tolist(),
        "data": df["total_pnl"].tolist(),
    }


def format_positions_for_chart(
    positions_history: List[Dict[str, Any]],
    symbol: str = "BTC/USDT",
) -> Dict[str, List[Any]]:
    """Format position size over time for Chart.js.

    Args:
        positions_history: List of position snapshots with 'timestamp' and 'size' fields.
        symbol: Trading pair symbol to filter by.

    Returns:
        Dictionary with 'labels' (ISO timestamps) and 'data' (position sizes).
    """
    if not positions_history:
        return {"labels": [], "data": []}

    df = pd.DataFrame(positions_history)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return {
        "labels": df["timestamp"].dt.isoformat().tolist(),
        "data": df["size"].tolist(),
    }


def format_trade_log_for_chart(
    trades: List[Dict[str, Any]],
) -> Dict[str, List[Any]]:
    """Format trade log for bar chart visualization.

    Args:
        trades: List of trade entries with 'timestamp' and 'pnl' fields.

    Returns:
        Dictionary with 'labels' (ISO timestamps) and 'data' (P&L values).
    """
    if not trades:
        return {"labels": [], "data": []}

    df = pd.DataFrame(trades)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return {
        "labels": df["timestamp"].dt.isoformat().tolist(),
        "data": df["pnl"].tolist() if "pnl" in df.columns else [],
    }