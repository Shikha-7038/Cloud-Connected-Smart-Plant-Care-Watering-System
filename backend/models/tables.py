"""Database tables (see docs/ARCHITECTURE.md for the ER diagram)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Index, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from cloud.database_service import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Always store UTC and always return timezone-aware datetimes (SQLite drops tz)."""
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    devices = relationship("Device", back_populates="owner")


class Device(Base):
    __tablename__ = "devices"
    device_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), index=True)
    plant_name: Mapped[str] = mapped_column(String(100))
    plant_type: Mapped[str] = mapped_column(String(30), default="INDOOR")
    location: Mapped[str] = mapped_column(String(100), default="")
    moisture_threshold: Mapped[float] = mapped_column(Float, default=30)
    auto_watering: Mapped[bool] = mapped_column(Boolean, default=True)
    api_key_hash: Mapped[str] = mapped_column(String(64))
    # live state
    last_seen: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    pump_on: Mapped[bool] = mapped_column(Boolean, default=False)
    pump_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_watering_end: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    last_watered_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    owner = relationship("User", back_populates="devices")


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    reading_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"))
    soil_moisture: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float] = mapped_column(Float)
    humidity: Mapped[float] = mapped_column(Float)
    light_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    water_tank_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime)
    # composite index = fast "latest / history of one device" queries;
    # UNIQUE also gives us duplicate-reading detection for free.
    __table_args__ = (UniqueConstraint("device_id", "timestamp", name="uq_device_ts"),
                      Index("ix_reading_device_ts", "device_id", "timestamp"))


class WateringEvent(Base):
    __tablename__ = "watering_events"
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), index=True)
    trigger_type: Mapped[str] = mapped_column(String(10))       # AUTO | MANUAL
    moisture_before: Mapped[float] = mapped_column(Float)
    moisture_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)   # seconds
    stop_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)  # start time
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Alert(Base):
    __tablename__ = "alerts"
    alert_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.device_id"), index=True)
    alert_type: Mapped[str] = mapped_column(String(30))   # LOW_MOISTURE | HIGH_TEMPERATURE | LOW_TANK | DEVICE_OFFLINE
    severity: Mapped[str] = mapped_column(String(10), default="WARNING")  # INFO | WARNING | CRITICAL
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(15), default="OPEN")  # OPEN | ACKNOWLEDGED | RESOLVED
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
