"""Health data portmanteau tool — log, query, trend, import.

Operations:
- log_record: Store a health data point.
- query: Search records by metric, time range, source.
- trend: Get trend analysis for a metric over N days.
- import_apple_health: Parse and import Apple Health export.xml.
- get_stats: DB summary + store health.
- log_vsm_event: Receive a VSM event from devices-mcp.
"""

import logging
from datetime import datetime
from typing import Any, Literal

from ..models.health import (
    HealthMetric,
    HealthRecord,
    TrendResult,
    VSMEvent,
    VSMDevice,
)
from ..services.health_store import get_store
from ..services.vsm_consumer import ingest_vsm_event

logger = logging.getLogger(__name__)


def register_health_tools(app):
    """Register health data tools."""

    @app.tool()
    async def health_data(
        operation: Literal[
            "log_record",
            "query",
            "trend",
            "import_apple_health",
            "get_stats",
            "log_vsm_event",
        ],
        metric: str = "",
        value: float | None = None,
        unit: str = "",
        source: str = "manual",
        source_device: str = "",
        notes: str = "",
        days: int = 7,
        limit: int = 100,
        file_path: str = "",
        device: str = "",
        event: str = "",
        confidence: float = 0.8,
        tags: str = "",
    ) -> dict[str, Any]:
        """Consolidated health data management.

        ## Operations
        - log_record: Store metric + value + optional notes/unit/source.
        - query: List records filtered by metric, time range, source.
        - trend: Average, min, max, direction over N days.
        - import_apple_health: Parse Apple Health export.xml (.zip or .xml).
        - get_stats: Record counts, VSM events, meals, DB size.
        - log_vsm_event: Ingest a camera-based state machine event.

        ## Return Format
        {"success": bool, "message": str, "result": {...}}

        ## Examples
        health_data(operation="log_record", metric="weight", value=72.5, unit="kg")
        health_data(operation="trend", metric="weight", days=30)
        health_data(operation="query", metric="heart_rate", days=1)
        """
        store = get_store()
        try:
            if operation == "log_record":
                hr = HealthRecord(
                    metric=HealthMetric(metric) if metric else HealthMetric.CUSTOM,
                    value=value,
                    unit=unit,
                    source=source,
                    source_device=source_device,
                    notes=notes,
                    tags=tags.split(",") if tags else [],
                )
                store.add_record(hr)
                return {"success": True, "message": f"Recorded {metric}={value} {unit}", "id": hr.id}

            if operation == "query":
                metric_enum = HealthMetric(metric) if metric else None
                records = store.query_records(metric=metric_enum, days=days, limit=limit, source=source or None)
                return {"success": True, "count": len(records), "records": records}

            if operation == "trend":
                if not metric:
                    return {"success": False, "error": "metric required for trend"}
                trend = store.query_trend(HealthMetric(metric), days=days)
                return {"success": True, "trend": trend.model_dump()}

            if operation == "import_apple_health":
                if not file_path:
                    return {"success": False, "error": "file_path required"}
                from ..services.apple_health import parse_export
                result = parse_export(file_path)
                return {"success": True, **result}

            if operation == "get_stats":
                stats = store.get_stats()
                return {"success": True, **stats}

            if operation == "log_vsm_event":
                if not device or not event:
                    return {"success": False, "error": "device and event required"}
                try:
                    vsm_dev = VSMDevice(device)
                except ValueError:
                    vsm_dev = VSMDevice.CUSTOM
                vsm_event = VSMEvent(
                    device=vsm_dev,
                    event=event,
                    value=value,
                    unit=unit,
                    confidence=confidence,
                    metadata={"notes": notes} if notes else {},
                )
                record_id = ingest_vsm_event(vsm_event)
                return {
                    "success": True,
                    "message": f"VSM event logged: {device}/{event}",
                    "record_id": record_id,
                }

            return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            logger.exception("health_data (%s) failed", operation)
            return {"success": False, "error": str(e)}
