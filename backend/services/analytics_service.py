"""Analytics over a time window: moisture stats, watering counts, uptime, water use."""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.tables import Device, SensorReading, WateringEvent
from backend.services.reading_service import latest_reading


def health_status(device: Device, soil: float | None) -> str:
    if soil is None:
        return "Unknown"
    if soil >= device.moisture_threshold:
        return "Healthy"
    return "Critical" if soil < device.moisture_threshold - 10 else "Needs Water"


def compute_analytics(db: Session, device: Device, hours: int, now: datetime,
                      expected_interval: float = 2.0) -> dict:
    since = now - timedelta(hours=hours)
    q = select(func.count(SensorReading.reading_id), func.avg(SensorReading.soil_moisture),
               func.min(SensorReading.soil_moisture), func.max(SensorReading.soil_moisture),
               func.avg(SensorReading.temperature), func.avg(SensorReading.humidity),
               func.min(SensorReading.timestamp)).where(
        SensorReading.device_id == device.device_id, SensorReading.timestamp >= since)
    n, avg_m, min_m, max_m, avg_t, avg_h, first = db.execute(q).one()

    events = db.scalars(select(WateringEvent).where(WateringEvent.device_id == device.device_id,
                                                    WateringEvent.timestamp >= since)).all()
    pump_seconds = sum(e.duration or 0 for e in events)

    uptime = None
    if n and first:
        first = first if first.tzinfo else first.replace(tzinfo=now.tzinfo)
        expected = max(1.0, (now - first).total_seconds() / expected_interval + 1)
        uptime = round(min(100.0, n / expected * 100), 1)

    latest = latest_reading(db, device.device_id)
    r = lambda v: None if v is None else round(v, 1)
    return {"window_hours": hours, "readings": n,
            "avg_moisture": r(avg_m), "min_moisture": r(min_m), "max_moisture": r(max_m),
            "avg_temperature": r(avg_t), "avg_humidity": r(avg_h),
            "watering_events": len(events),
            "daily_watering_frequency": round(len(events) / max(hours / 24, 1 / 24), 2),
            "water_used_ml": round(pump_seconds * settings.PUMP_FLOW_ML_PER_SEC),
            "device_uptime_pct": uptime,
            "plant_health": health_status(device, latest.soil_moisture if latest else None)}
