"""Core pipeline: validate -> store -> automation -> alerts -> pump command."""
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from automation.plant_profiles import get_profile
from automation.watering_engine import EngineConfig, Decision, evaluate, target_moisture
from backend.config import settings
from backend.models.schemas import SensorIn
from backend.models.tables import Device, SensorReading, WateringEvent
from backend.services.alert_service import resolve_alerts, sync_alerts

log = logging.getLogger("plantcare.pipeline")

ENGINE_CFG = EngineConfig(max_watering_seconds=settings.MAX_WATERING_SECONDS,
                          cooldown_seconds=settings.COOLDOWN_SECONDS,
                          min_tank_level=settings.MIN_TANK_LEVEL)


def target_for(device: Device) -> float:
    return target_moisture(device.moisture_threshold, get_profile(device.plant_type)["target_margin"], ENGINE_CFG)


def open_event(db: Session, device_id: str) -> WateringEvent | None:
    return db.scalar(select(WateringEvent).where(WateringEvent.device_id == device_id,
                                                 WateringEvent.ended_at.is_(None))
                     .order_by(WateringEvent.event_id.desc()))


def start_pump(db: Session, device: Device, soil: float, trigger: str, now: datetime) -> WateringEvent:
    device.pump_on, device.pump_started_at = True, now
    ev = WateringEvent(device_id=device.device_id, trigger_type=trigger,
                       moisture_before=soil, timestamp=now)
    db.add(ev)
    log.info("PUMP ON  %s (%s) soil=%.1f", device.device_id, trigger, soil)
    return ev


def stop_pump(db: Session, device: Device, soil: float, reason: str, now: datetime) -> None:
    ev = open_event(db, device.device_id)
    if ev:
        ev.ended_at, ev.moisture_after, ev.stop_reason = now, soil, reason
        ev.duration = round((now - ev.timestamp).total_seconds(), 2)
    device.pump_on, device.pump_started_at = False, None
    device.last_watering_end = device.last_watered_at = now
    log.info("PUMP OFF %s (%s) soil=%.1f", device.device_id, reason, soil)


def latest_reading(db: Session, device_id: str) -> SensorReading | None:
    return db.scalar(select(SensorReading).where(SensorReading.device_id == device_id)
                     .order_by(SensorReading.timestamp.desc()).limit(1))


def process_reading(db: Session, device: Device, data: SensorIn, now: datetime) -> dict:
    ts = data.timestamp or now
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=now.tzinfo)
    if ts > now + timedelta(minutes=5):
        raise ValueError("timestamp is in the future")

    reading = SensorReading(device_id=device.device_id, soil_moisture=data.soil_moisture,
                            temperature=data.temperature, humidity=data.humidity,
                            light_level=data.light_level, water_tank_level=data.water_tank_level,
                            timestamp=ts)
    db.add(reading)
    try:
        db.flush()
    except IntegrityError:                       # same device + timestamp already stored
        db.rollback()
        log.info("duplicate reading ignored for %s at %s", device.device_id, ts)
        return {"status": "duplicate", "pump": "ON" if device.pump_on else "OFF"}

    device.last_seen = now                       # heartbeat (server clock is trusted)
    resolve_alerts(db, device.device_id, "DEVICE_OFFLINE", now)

    latest = latest_reading(db, device.device_id)
    is_newest = latest is None or latest.reading_id == reading.reading_id
    decision = Decision("NONE", "historical_reading")
    if is_newest:                                # late/buffered readings never drive the pump
        decision = evaluate(soil=data.soil_moisture, tank=data.water_tank_level,
                            threshold=device.moisture_threshold, target=target_for(device),
                            auto_enabled=device.auto_watering, pump_on=device.pump_on,
                            pump_started_at=device.pump_started_at,
                            last_watering_end=device.last_watering_end, now=now, cfg=ENGINE_CFG)
        if decision.action == "START":
            start_pump(db, device, data.soil_moisture, "AUTO", now)
        elif decision.action == "STOP":
            stop_pump(db, device, data.soil_moisture, decision.reason, now)
        sync_alerts(db, device, reading, now)

    db.commit()
    return {"status": "stored", "reading_id": reading.reading_id,
            "pump": "ON" if device.pump_on else "OFF", "decision": decision.reason}


def start_manual_watering(db: Session, device: Device, now: datetime) -> WateringEvent:
    """Manual watering still respects safety rules (no overwatering, tank, one pump run at a time)."""
    latest = latest_reading(db, device.device_id)
    if latest is None:
        raise PermissionError("No sensor data yet - cannot water safely")
    if device.pump_on:
        raise PermissionError("Pump is already running")
    if latest.water_tank_level is not None and latest.water_tank_level < settings.MIN_TANK_LEVEL:
        raise PermissionError("Water tank is too low")
    if latest.soil_moisture >= target_for(device):
        raise PermissionError("Soil is already moist enough - overwatering prevented")
    ev = start_pump(db, device, latest.soil_moisture, "MANUAL", now)
    db.commit()
    db.refresh(ev)
    return ev
