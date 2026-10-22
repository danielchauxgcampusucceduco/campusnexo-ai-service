"""HTTP request contracts for the public API."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.settings import (
    MAX_ASSIGNMENT_COURSES,
    MAX_ASSIGNMENT_ROOMS,
    MAX_ASSIGNMENT_ATTENDANCE,
    MAX_ROOM_CAPACITY,
    MAX_ROOM_POWER_KW,
    MAX_OCCUPANCY_BATCH_ITEMS,
    MAX_THERMAL_HORIZON_MINUTES,
    MIN_THERMAL_PARAMETER,
)


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OccupancyInput(StrictInput):
    space_id: str = Field(min_length=1, max_length=32)
    yolo_people: int | None = Field(default=None, ge=0, le=1000, strict=True)
    co2_ppm: float = Field(ge=0, le=10000, strict=True)
    wifi_devices: int = Field(ge=0, le=10000, strict=True)
    outdoor_co2_ppm: float = Field(default=415, ge=300, le=1000, strict=True)

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


class ThermalInput(StrictInput):
    current_temp_c: float = Field(ge=-20, le=60, strict=True)
    outside_temp_c: float = Field(ge=-30, le=60, strict=True)
    occupancy: int = Field(ge=0, le=1000, strict=True)
    lighting_kw: float = Field(ge=0, le=100, strict=True)
    resistance_c_per_kw: float = Field(default=2.4, ge=MIN_THERMAL_PARAMETER, le=1000, strict=True)
    capacitance_kwh_per_c: float = Field(default=1.85, ge=MIN_THERMAL_PARAMETER, le=1000, strict=True)
    comfort_limit_c: float = Field(default=24.5, ge=10, le=35, strict=True)
    horizon_min: int = Field(default=20, ge=1, le=MAX_THERMAL_HORIZON_MINUTES, strict=True)


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


class OccupancyEstimateOutput(BaseModel):
    space_id: str
    occupancy_estimate: int = Field(ge=0)
    confidence_pct: float = Field(ge=0, le=100)
    confidence_meaning: str
    method: str
    camera_available: bool
    is_estimate: Literal[True]
    note: str


class OccupancyBatchOutput(BaseModel):
    estimates: list[OccupancyEstimateOutput]


class ThermalRecommendationOutput(BaseModel):
    model: Literal["1R1C_exact_exponential"]
    safe_off_duration_min: int = Field(ge=0, le=120)
    projected_temp_at_horizon_c: float
    initial_rate_c_per_min: float
    comfort_limit_c: float
    note: str


class DeskStateOutput(BaseModel):
    state: Literal[
        "OCCUPIED_VERIFIED",
        "POSSIBLE_ABANDONMENT",
        "RELEASE_RECOMMENDED",
        "AVAILABLE",
    ]
    is_automatic_release: Literal[False]
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
