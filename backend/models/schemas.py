"""Request / response schemas with validation (Pydantic)."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

ID_PATTERN = r"^[A-Za-z0-9_-]+$"


class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str
    password: str


class SensorIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64, pattern=ID_PATTERN)
    soil_moisture: float = Field(ge=0, le=100)
    temperature: float = Field(ge=-40, le=85)
    humidity: float = Field(ge=0, le=100)
    light_level: float | None = Field(default=None, ge=0, le=100)
    water_tank_level: float | None = Field(default=None, ge=0, le=100)
    timestamp: datetime | None = None


class DeviceIn(BaseModel):
    device_id: str = Field(min_length=1, max_length=64, pattern=ID_PATTERN)
    plant_name: str = Field(min_length=1, max_length=100)
    plant_type: str = "INDOOR"
    location: str = Field(default="", max_length=100)
    moisture_threshold: float | None = Field(default=None, ge=0, le=100)


class ThresholdIn(BaseModel):
    moisture_threshold: float = Field(ge=0, le=100)


class AutoIn(BaseModel):
    auto_watering: bool


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    reading_id: int
    device_id: str
    soil_moisture: float
    temperature: float
    humidity: float
    light_level: float | None
    water_tank_level: float | None
    timestamp: datetime


class WateringEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    event_id: int
    device_id: str
    trigger_type: str
    moisture_before: float
    moisture_after: float | None
    duration: float | None
    stop_reason: str | None
    timestamp: datetime
    ended_at: datetime | None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    alert_id: int
    device_id: str
    alert_type: str
    severity: str
    message: str
    status: str
    created_at: datetime
    resolved_at: datetime | None
