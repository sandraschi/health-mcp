"""Prefab UI cards for health-mcp."""

import logging
from typing import Any

from fastmcp.server.server import ToolResult
from prefab_ui import PrefabApp
from prefab_ui.components import Card, Div, Heading, Row

from ..services.health_store import get_store

logger = logging.getLogger(__name__)


def register_prefab_tools(app):
    """Register Prefab UI tools."""

    @app.tool(app=True)
    async def show_health_dashboard() -> ToolResult:
        """Display a health summary card with recent metrics, trends, and store stats."""
        store = get_store()
        stats = store.get_stats()
        recent_weight = store.query_records(metric="weight", days=7, limit=5)
        recent_hr = store.query_records(metric="heart_rate", days=1, limit=10)

        with PrefabApp(title="Health Dashboard") as app_card:
            Heading("Summary")
            Row(label="Health Records", value=str(stats["health_records"]))
            Row(label="VSM Events", value=str(stats["vsm_events"]))
            Row(label="Meals Logged", value=str(stats["meals"]))
            Row(label="DB Size", value=f"{stats['db_size_bytes'] / 1024:.0f} KB")

            if recent_weight:
                Heading("Recent Weight")
                for r in recent_weight[:3]:
                    ts = r.get("timestamp", "?")[:10]
                    val = r.get("value", "?")
                    Div(f"{ts}: {val} kg")

            if recent_hr:
                Heading("Heart Rate (today)")
                vals = [r.get("value") for r in recent_hr if r.get("value")]
                if vals:
                    Div(f"Avg: {sum(vals) / len(vals):.0f} bpm, Range: {min(vals)}-{max(vals)} bpm")

        return ToolResult(content="Health dashboard card rendered.", structured_content=app_card)
