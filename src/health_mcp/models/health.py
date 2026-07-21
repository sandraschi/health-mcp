"""Health data models for health-mcp."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class HealthMetric(str, Enum):
    WEIGHT = "weight"
    SLEEP_START = "sleep_start"
    SLEEP_END = "sleep_end"
    MEAL = "meal"
    WATER = "water"
    STEPS = "steps"
    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE = "blood_pressure"
    MOOD = "mood"
    SYMPTOM = "symptom"
    PET_FEEDING = "pet_feeding"
    PET_ACTIVITY = "pet_activity"
    MEDICATION = "medication"
    EXERCISE = "exercise"
    CUSTOM = "custom"


class VSMDevice(str, Enum):
    SCALE = "scale"
    FRIDGE = "fridge"
    TOASTER = "toaster"
    DOOR = "door"
    DOG_BOWL = "dog_bowl"
    COFFEE = "coffee_machine"
    BEDROOM = "bedroom"
    CUSTOM = "custom"


class HealthRecord(BaseModel):
    """A single health data point from any source."""

    id: str = Field(default="", description="Unique record ID (auto-generated)")
    metric: HealthMetric = Field(..., description="Type of health metric")
    value: float | str | None = Field(None, description="Measured value")
    unit: str = Field("", description="Unit of measurement (kg, min, bpm, etc.)")
    source: str = Field("manual", description="Source: vsm, apple_health, manual")
    source_device: str = Field("", description="Specific device ID (e.g. scale-usb-001)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the measurement was taken")
    notes: str = Field("", description="Free-text notes")
    tags: list[str] = Field(default_factory=list, description="Arbitrary tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Extra source-specific data")

    def model_dump_json(self, **kwargs) -> str:
        return super().model_dump_json(**kwargs)


class VSMEvent(BaseModel):
    """Event from a Visual State Machine camera watcher."""

    device: VSMDevice = Field(..., description="Device that triggered the event")
    event: str = Field(..., description="Event type (weigh_in, ate_meal, slept, etc.)")
    value: float | str | None = Field(None, description="Measured value if applicable")
    unit: str = Field("", description="Unit if applicable")
    confidence: float = Field(0.8, description="Detection confidence 0-1")
    timestamp: datetime = Field(default_factory=datetime.now)
    snapshot_url: str = Field("", description="Optional camera snapshot URL")
    metadata: dict[str, Any] = Field(default_factory=dict)


class MealRecord(BaseModel):
    """A meal event — start/end times and inferred contents."""

    id: str = ""
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: datetime | None = Field(None)
    meal_type: str = Field("unknown", description="breakfast, lunch, dinner, snack")
    inferred: bool = Field(False, description="Detected by VSM vs manually logged")
    duration_min: int = Field(0)
    notes: str = ""


class TrendResult(BaseModel):
    """Simple trend analysis result."""

    metric: HealthMetric
    period_days: int = 7
    count: int = 0
    avg: float | None = None
    min_val: float | None = None
    max_val: float | None = None
    trend: str = "stable"  # up, down, stable, insufficient_data
    recent: list[dict[str, Any]] = Field(default_factory=list)
