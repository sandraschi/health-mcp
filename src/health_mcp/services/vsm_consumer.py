"""VSM event consumer — receives camera-based state machine events
from devices-mcp and translates them into health records.

Maps VSM device events to HealthMetric records:
  - scale/weigh_in -> weight
  - fridge/open + close -> meal timing
  - dog_bowl/empty -> pet_feeding
  - bedroom/door_open -> sleep_end (approximate)
"""

import logging
from datetime import datetime

from ..models.health import (
    HealthMetric,
    HealthRecord,
    MealRecord,
    VSMEvent,
)
from .health_store import get_store

logger = logging.getLogger(__name__)


def ingest_vsm_event(event: VSMEvent) -> str | None:
    """Process a VSM event and store the resulting health record(s).

    Returns the record ID if a health record was created, None if the event
    was informational-only (e.g. fridge open without meal context).
    """
    store = get_store()
    store.add_vsm_event(event)
    record_id = None

    if event.device.value == "scale" and event.event == "weigh_in":
        hr = HealthRecord(
            metric=HealthMetric.WEIGHT,
            value=event.value,
            unit=event.unit or "kg",
            source="vsm",
            source_device=event.device.value,
            timestamp=event.timestamp,
            metadata={"confidence": event.confidence, "snapshot_url": event.snapshot_url},
        )
        store.add_record(hr)
        record_id = hr.id
        logger.info("Weight recorded: %s %s", event.value, event.unit)

    elif event.device.value == "dog_bowl" and event.event == "empty":
        hr = HealthRecord(
            metric=HealthMetric.PET_FEEDING,
            value=0,
            unit="refill_needed",
            source="vsm",
            source_device="dog_bowl",
            timestamp=event.timestamp,
            notes="Bowl empty — refill needed",
        )
        store.add_record(hr)
        record_id = hr.id
        logger.info("Dog bowl empty — refill needed")

    elif event.device.value == "fridge" and event.event == "opened":
        pass  # Fridge open alone is not a meal — needs duration context

    elif event.device.value == "bedroom" and event.event == "door_opened":
        hr = HealthRecord(
            metric=HealthMetric.SLEEP_END,
            value=0,
            unit="wake",
            source="vsm",
            source_device="bedroom_cam",
            timestamp=event.timestamp,
            notes="Woke up (VSM detection)",
            tags=["vsm"],
        )
        store.add_record(hr)
        record_id = hr.id

    return record_id


def infer_meal(fridge_open_time: datetime, fridge_close_time: datetime) -> MealRecord:
    """Infer a meal from fridge open/close duration."""
    duration = int((fridge_close_time - fridge_open_time).total_seconds() / 60)
    hour = fridge_open_time.hour

    if hour < 10:
        meal_type = "breakfast"
    elif hour < 14:
        meal_type = "lunch"
    elif hour < 18:
        meal_type = "snack"
    else:
        meal_type = "dinner"

    meal = MealRecord(
        start_time=fridge_open_time,
        end_time=fridge_close_time,
        meal_type=meal_type,
        inferred=True,
        duration_min=duration,
    )
    store = get_store()
    store.add_meal(meal)
    return meal
