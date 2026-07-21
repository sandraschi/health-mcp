"""Apple Health XML export parser.

Parses the export.xml from an Apple Health Export (Settings > Health > Export All Health Data).
Stores records into the local health-mcp SQLite store.
"""

import logging
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from ..models.health import HealthMetric, HealthRecord
from .health_store import get_store

logger = logging.getLogger(__name__)

_METRIC_MAP: dict[str, HealthMetric] = {
    "HKQuantityTypeIdentifierBodyMass": HealthMetric.WEIGHT,
    "HKQuantityTypeIdentifierHeartRate": HealthMetric.HEART_RATE,
    "HKQuantityTypeIdentifierStepCount": HealthMetric.STEPS,
    "HKQuantityTypeIdentifierBloodPressureSystolic": HealthMetric.BLOOD_PRESSURE,
    "HKQuantityTypeIdentifierBloodPressureDiastolic": HealthMetric.BLOOD_PRESSURE,
    "HKCategoryTypeIdentifierSleepAnalysis": HealthMetric.SLEEP_START,
    "HKQuantityTypeIdentifierDietaryWater": HealthMetric.WATER,
    "HKQuantityTypeIdentifierActiveEnergyBurned": HealthMetric.EXERCISE,
    "HKQuantityTypeIdentifierDietaryEnergyConsumed": HealthMetric.MEAL,
}

_UNIT_MAP: dict[str, str] = {
    "kg": "kg",
    "lb": "lb",
    "count/min": "bpm",
    "count": "steps",
    "mmHg": "mmHg",
    "mL": "mL",
    "kcal": "kcal",
}


def parse_export(file_path: str | Path, max_records: int = 10000) -> dict[str, Any]:
    """Parse an Apple Health export.xml (or .zip) and store records.

    Args:
        file_path: Path to export.xml or export.zip
        max_records: Max records to import (Apple exports can be huge)

    Returns:
        {imported, skipped, errors, types_imported}
    """
    path = Path(file_path)
    if not path.exists():
        return {"imported": 0, "error": f"File not found: {path}"}

    xml_path = path
    if path.suffix == ".zip":
        try:
            with zipfile.ZipFile(path) as zf:
                zf.extract("export.xml", path.parent)
                xml_path = path.parent / "export.xml"
        except Exception as e:
            return {"imported": 0, "error": f"Failed to extract zip: {e}"}

    try:
        tree = ElementTree.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        return {"imported": 0, "error": f"Failed to parse XML: {e}"}

    store = get_store()
    imported = 0
    skipped = 0
    errors = 0
    types_imported: set[str] = set()

    for record_elem in root.iter("Record"):
        if imported >= max_records:
            break

        type_name = record_elem.get("type", "")
        metric = _METRIC_MAP.get(type_name)
        if not metric:
            skipped += 1
            continue

        try:
            value_str = record_elem.get("value", "0")
            value = float(value_str) if "." in value_str or value_str.isdigit() else value_str
            unit = _UNIT_MAP.get(record_elem.get("unit", ""), record_elem.get("unit", ""))
            start_date_str = record_elem.get("startDate", "") or record_elem.get("creationDate", "")
            from datetime import datetime

            ts = datetime.fromisoformat(start_date_str.replace("Z", "+00:00")) if start_date_str else datetime.now()

            hr = HealthRecord(
                metric=metric,
                value=value,
                unit=unit,
                source="apple_health",
                timestamp=ts,
                metadata={"apple_type": type_name},
            )
            store.add_record(hr)
            imported += 1
            types_imported.add(type_name)
        except Exception as e:
            logger.warning("Failed to parse Apple Health record: %s", e)
            errors += 1

    logger.info(
        "Apple Health import: %d records, %d skipped, %d errors, %d types",
        imported, skipped, errors, len(types_imported),
    )
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors,
        "types_imported": list(types_imported),
    }
