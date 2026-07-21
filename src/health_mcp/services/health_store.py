"""SQLite-backed health data store.

Stores health records, VSM events, meals, and trends.
Thread-safe for concurrent MCP tool access.
"""

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from ..models.health import (
    HealthMetric,
    HealthRecord,
    MealRecord,
    TrendResult,
    VSMEvent,
)

logger = logging.getLogger(__name__)

_DB_PATH = Path.home() / ".health-mcp" / "health.db"


class HealthStore:
    """Thread-safe SQLite store for health data."""

    def __init__(self, db_path: str | Path = ""):
        self._db_path = Path(db_path) if db_path else _DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._lock:
            conn = self._conn()
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS health_records (
                    id TEXT PRIMARY KEY,
                    metric TEXT NOT NULL,
                    value REAL,
                    value_text TEXT,
                    unit TEXT,
                    source TEXT DEFAULT 'manual',
                    source_device TEXT,
                    timestamp TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    metadata TEXT DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS vsm_events (
                    id TEXT PRIMARY KEY,
                    device TEXT NOT NULL,
                    event TEXT NOT NULL,
                    value REAL,
                    unit TEXT,
                    confidence REAL DEFAULT 0.8,
                    timestamp TEXT NOT NULL,
                    snapshot_url TEXT DEFAULT '',
                    metadata TEXT DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS meals (
                    id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    meal_type TEXT DEFAULT 'unknown',
                    inferred INTEGER DEFAULT 0,
                    duration_min INTEGER DEFAULT 0,
                    notes TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_records_metric ON health_records(metric);
                CREATE INDEX IF NOT EXISTS idx_records_timestamp ON health_records(timestamp);
                CREATE INDEX IF NOT EXISTS idx_vsm_timestamp ON vsm_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_meals_start ON meals(start_time);
            """)
            conn.commit()
            conn.close()

    def add_record(self, record: HealthRecord) -> HealthRecord:
        if not record.id:
            record.id = f"hr_{uuid.uuid4().hex[:12]}"
        with self._lock:
            conn = self._conn()
            conn.execute(
                """INSERT OR REPLACE INTO health_records
                   (id, metric, value, value_text, unit, source, source_device, timestamp, notes, tags, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.id,
                    record.metric.value,
                    record.value if isinstance(record.value, (int, float)) else None,
                    str(record.value) if not isinstance(record.value, (int, float)) else None,
                    record.unit,
                    record.source,
                    record.source_device,
                    record.timestamp.isoformat(),
                    record.notes,
                    json.dumps(record.tags),
                    json.dumps(record.metadata),
                ),
            )
            conn.commit()
            conn.close()
        return record

    def add_vsm_event(self, event: VSMEvent) -> str:
        event_id = f"vsm_{uuid.uuid4().hex[:12]}"
        with self._lock:
            conn = self._conn()
            conn.execute(
                """INSERT INTO vsm_events
                   (id, device, event, value, unit, confidence, timestamp, snapshot_url, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event_id,
                    event.device.value,
                    event.event,
                    event.value if isinstance(event.value, (int, float)) else None,
                    event.unit,
                    event.confidence,
                    event.timestamp.isoformat(),
                    event.snapshot_url,
                    json.dumps(event.metadata),
                ),
            )
            conn.commit()
            conn.close()
        return event_id

    def add_meal(self, meal: MealRecord) -> MealRecord:
        if not meal.id:
            meal.id = f"meal_{uuid.uuid4().hex[:12]}"
        with self._lock:
            conn = self._conn()
            conn.execute(
                """INSERT OR REPLACE INTO meals
                   (id, start_time, end_time, meal_type, inferred, duration_min, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    meal.id,
                    meal.start_time.isoformat(),
                    meal.end_time.isoformat() if meal.end_time else None,
                    meal.meal_type,
                    1 if meal.inferred else 0,
                    meal.duration_min,
                    meal.notes,
                ),
            )
            conn.commit()
            conn.close()
        return meal

    def query_records(
        self,
        metric: HealthMetric | str | None = None,
        days: int = 7,
        limit: int = 100,
        source: str | None = None,
    ) -> list[dict[str, Any]]:
        from_date = (datetime.now() - timedelta(days=days)).isoformat()
        params: list[Any] = [from_date]
        sql = "SELECT * FROM health_records WHERE timestamp >= ?"
        if metric:
            sql += " AND metric = ?"
            params.append(metric.value if isinstance(metric, HealthMetric) else metric)
        if source:
            sql += " AND source = ?"
            params.append(source)
        sql += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._lock:
            conn = self._conn()
            rows = conn.execute(sql, params).fetchall()
            conn.close()
        return [dict(r) for r in rows]

    def query_trend(self, metric: HealthMetric, days: int = 7) -> TrendResult:
        records = self.query_records(metric=metric, days=days)
        values = [
            r["value"] for r in records
            if r["value"] is not None and isinstance(r["value"], (int, float))
        ]
        result = TrendResult(metric=metric, period_days=days, count=len(values))
        if values:
            result.avg = round(sum(values) / len(values), 2)
            result.min_val = min(values)
            result.max_val = max(values)
            if len(values) >= 3:
                half = len(values) // 2
                first_half = sum(values[:half]) / half
                second_half = sum(values[half:]) / (len(values) - half)
                diff = second_half - first_half
                result.trend = "up" if diff > result.avg * 0.05 else "down" if diff < -result.avg * 0.05 else "stable"
            result.recent = records[:10]
        else:
            result.trend = "insufficient_data"
        return result

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            conn = self._conn()
            record_count = conn.execute("SELECT COUNT(*) FROM health_records").fetchone()[0]
            vsm_count = conn.execute("SELECT COUNT(*) FROM vsm_events").fetchone()[0]
            meal_count = conn.execute("SELECT COUNT(*) FROM meals").fetchone()[0]
            db_size = self._db_path.stat().st_size if self._db_path.exists() else 0
            conn.close()
        return {
            "health_records": record_count,
            "vsm_events": vsm_count,
            "meals": meal_count,
            "db_size_bytes": db_size,
            "db_path": str(self._db_path),
        }


_store: HealthStore | None = None


def get_store() -> HealthStore:
    global _store
    if _store is None:
        _store = HealthStore()
    return _store
