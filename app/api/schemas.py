"""HTTP request contracts for the public API."""
from pydantic import BaseModel, Field


class OccupancyInput(BaseModel):
    space_id: str = Field(min_length=1, max_length=32)
    yolo_people: int | None = Field(default=None, ge=0, le=1000)
    co2_ppm: float = Field(ge=0, le=10000)
    wifi_devices: int = Field(ge=0, le=10000)
    outdoor_co2_ppm: float = Field(default=415, ge=300, le=1000)


class ThermalInput(BaseModel):
    current_temp_c: float = Field(ge=-20, le=60)
    outside_temp_c: float = Field(ge=-30, le=60)
    occupancy: int = Field(ge=0, le=1000)
    lighting_kw: float = Field(ge=0, le=100)
    resistance_c_per_kw: float = Field(default=2.4, gt=0, le=1000)
    capacitance_kwh_per_c: float = Field(default=1.85, gt=0, le=1000)
    comfort_limit_c: float = Field(default=24.5, ge=10, le=35)
    horizon_min: int = Field(default=20, ge=1, le=120)


class AssignmentInput(BaseModel):
    courses: list["CourseAssignmentInput"] = Field(max_length=18)
    rooms: list["RoomAssignmentInput"]
    safety_margin: float = Field(default=1.10, gt=0, le=2)


class CourseAssignmentInput(BaseModel):
    course_id: str = Field(min_length=1, max_length=64)
    attendance: int = Field(ge=0, le=1000)


class RoomAssignmentInput(BaseModel):
    room_id: str = Field(min_length=1, max_length=64)
    capacity: int = Field(ge=0, le=1000)
    power_kw: float = Field(ge=0, le=1000)


AssignmentInput.model_rebuild()
