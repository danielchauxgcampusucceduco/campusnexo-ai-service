"""HTTP request contracts for the public API."""
from datetime import datetime
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.settings import (
    MAX_ANOMALY_READINGS,
    MAX_ASSIGNMENT_COURSES,
    MAX_ASSIGNMENT_ROOMS,
    MAX_ASSIGNMENT_ATTENDANCE,
    MAX_FORECAST_HISTORY,
    MAX_FORECAST_HOURS,
    MAX_ROOM_CAPACITY,
    MAX_ROOM_POWER_KW,
    MAX_OCCUPANCY_BATCH_ITEMS,
)


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OccupancyInput(StrictInput):
    """Raw measurements of one room. ``yolo_people`` is the camera's own count, never a fused estimate."""
    space_id: str = Field(min_length=1, max_length=32)
    yolo_people: int | None = Field(default=None, ge=0, le=1000, strict=True)
    co2_ppm: float = Field(ge=0, le=10000, strict=True)
    wifi_devices: int = Field(ge=0, le=10000, strict=True)
    outdoor_co2_ppm: float = Field(default=420, ge=300, le=1000, strict=True)
    area_sqm: float = Field(gt=0, le=100000, strict=True)
    capacity: int = Field(ge=1, le=5000, strict=True)

    @field_validator("space_id")
    @classmethod
    def normalize_space_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("space_id no puede estar vacío")
        return normalized


class OccupancyBatchInput(StrictInput):
    measurements: list[OccupancyInput] = Field(min_length=1, max_length=MAX_OCCUPANCY_BATCH_ITEMS)

    @model_validator(mode="after")
    def unique_spaces(self):
        space_ids = [measurement.space_id for measurement in self.measurements]
        if len(space_ids) != len(set(space_ids)):
            raise ValueError("space_id debe ser único dentro de measurements")
        return self


class AssignmentInput(StrictInput):
    courses: list["CourseAssignmentInput"] = Field(max_length=MAX_ASSIGNMENT_COURSES)
    rooms: list["RoomAssignmentInput"] = Field(max_length=MAX_ASSIGNMENT_ROOMS)
    safety_margin: float = Field(default=1.10, gt=0, le=2, strict=True)

    @model_validator(mode="after")
    def unique_identifiers(self):
        course_ids = [course.course_id for course in self.courses]
        room_ids = [room.room_id for room in self.rooms]
        if len(course_ids) != len(set(course_ids)):
            raise ValueError("course_id debe ser único dentro de courses")
        if len(room_ids) != len(set(room_ids)):
            raise ValueError("room_id debe ser único dentro de rooms")
        return self


class CourseAssignmentInput(StrictInput):
    course_id: str = Field(min_length=1, max_length=64)
    attendance: int = Field(ge=0, le=MAX_ASSIGNMENT_ATTENDANCE, strict=True)

    @field_validator("course_id")
    @classmethod
    def normalize_course_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("course_id no puede estar vacío")
        return normalized


class RoomAssignmentInput(StrictInput):
    room_id: str = Field(min_length=1, max_length=64)
    capacity: int = Field(ge=1, le=MAX_ROOM_CAPACITY, strict=True)
    power_kw: float = Field(ge=0, le=MAX_ROOM_POWER_KW, strict=True)

    @field_validator("room_id")
    @classmethod
    def normalize_room_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("room_id no puede estar vacío")
        return normalized


class AssignmentRecordOutput(BaseModel):
    course_id: str
    room_id: str
    attendance: int
    capacity: int
    utilization_pct: float
    nominal_power_kw: float


class AssignmentOutput(BaseModel):
    feasible: bool
    assignments: list[AssignmentRecordOutput]
    total_nominal_power_kw: float | None = None
    objective: str | None = None
    reason: str | None = None
    note: str | None = None


class OccupancySourceOutput(BaseModel):
    source: Literal["camara_yolo", "co2_balance_masico", "wifi_dispositivos"]
    people: float
    variance: float
    weight: float = Field(ge=0, le=1)


class OccupancyEstimateOutput(BaseModel):
    space_id: str
    occupancy_estimate: int = Field(ge=0)
    confidence_pct: float = Field(ge=0, le=100)
    sigma_people: float = Field(ge=0)
    confidence_meaning: str
    method: str
    camera_available: bool
    is_estimate: Literal[True]
    sources: list[OccupancySourceOutput]
    note: str


class OccupancyBatchOutput(BaseModel):
    estimates: list[OccupancyEstimateOutput]


class SensorReadingInput(StrictInput):
    """One stored reading of a room. Values are checked for plausibility, not rejected: that is the point."""
    space_id: str = Field(min_length=1, max_length=32)
    timestamp: AwareDatetime
    co2_ppm: float = Field(allow_inf_nan=False, strict=True)
    temperature_c: float = Field(allow_inf_nan=False, strict=True)
    humidity_pct: float = Field(allow_inf_nan=False, strict=True)
    illuminance_lux: float = Field(allow_inf_nan=False, strict=True)
    active_power_kw: float = Field(allow_inf_nan=False, strict=True)


class AnomaliesInput(StrictInput):
    readings: list[SensorReadingInput] = Field(max_length=MAX_ANOMALY_READINGS)


class AnomalyOutput(BaseModel):
    space_id: str
    sensor: str
    timestamp: datetime
    kind: Literal["FUERA_DE_RANGO", "VALOR_PEGADO", "SALTO"]
    value: float
    detail: str


class AnomaliesOutput(BaseModel):
    anomalies: list[AnomalyOutput]
    readings_analyzed: int
    method: str


class OccupancySampleInput(StrictInput):
    timestamp: AwareDatetime
    people: int = Field(ge=0, le=5000, strict=True)


class ForecastInput(StrictInput):
    space_id: str = Field(min_length=1, max_length=32)
    capacity: int = Field(ge=1, le=5000, strict=True)
    timezone: str = Field(default="America/Bogota", min_length=1, max_length=64)
    horizon_hours: int = Field(default=12, ge=1, le=MAX_FORECAST_HOURS, strict=True)
    history: list[OccupancySampleInput] = Field(min_length=1, max_length=MAX_FORECAST_HISTORY)


class ForecastPointOutput(BaseModel):
    timestamp: datetime
    people: float
    low: float
    high: float


class ForecastOutput(BaseModel):
    space_id: str
    method: str
    samples_used: int
    points: list[ForecastPointOutput]
    note: str


class CapabilityFeature(BaseModel):
    name: str
    mode: str
    summary: str


class CapabilitiesOutput(BaseModel):
    service: str
    api_version: str
    features: list[CapabilityFeature]
    limits: dict[str, int]


AssignmentInput.model_rebuild()
