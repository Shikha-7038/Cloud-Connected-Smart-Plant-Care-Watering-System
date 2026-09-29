"""Alert generation and auto-resolution. Alerts live in the cloud database."""
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from automation.plant_profiles import get_profile
from backend.config import settings
from backend.models.tables import Alert, Device, SensorReading

log = logging.getLogger("plantcare.alerts")


def open_alert(db: Session, device: Device, alert_type: str, severity: str,
               message: str, now: datetime) -> Alert | None:
    """Create an alert unless an unresolved one of the same type already exists (no spam)."""
    existing = db.scalar(select(Alert).where(Alert.device_id == device.device_id,
                                             Alert.alert_type == alert_type,
                                             Alert.status != "RESOLVED"))
    if existing:
        return None
    alert = Alert(device_id=device.device_id, alert_type=alert_type, severity=severity,
                  message=message, status="OPEN", created_at=now)
    db.add(alert)
    log.warning("ALERT %s %s: %s", severity, device.device_id, message)
    return alert


def resolve_alerts(db: Session, device_id: str, alert_type: str, now: datetime) -> None:
    rows = db.scalars(select(Alert).where(Alert.device_id == device_id,
                                          Alert.alert_type == alert_type,
                                          Alert.status != "RESOLVED")).all()
    for a in rows:
        a.status, a.resolved_at = "RESOLVED", now


def sync_alerts(db: Session, device: Device, r: SensorReading, now: datetime) -> None:
    """Raise or clear alerts based on the newest reading."""
    name, thr = device.plant_name, device.moisture_threshold

    if r.soil_moisture < thr:
        sev = "CRITICAL" if r.soil_moisture < thr - 10 else "WARNING"
        open_alert(db, device, "LOW_MOISTURE", sev, f"{name} moisture dropped below {thr:g}% (now {r.soil_moisture:.0f}%).", now)
    else:
        resolve_alerts(db, device.device_id, "LOW_MOISTURE", now)

    max_temp = get_profile(device.plant_type)["max_temp"]
    if r.temperature > max_temp:
        sev = "CRITICAL" if r.temperature > max_temp + 5 else "WARNING"
        open_alert(db, device, "HIGH_TEMPERATURE", sev, f"{name} temperature exceeded configured threshold ({r.temperature:.1f}°C > {max_temp:g}°C).", now)
    else:
        resolve_alerts(db, device.device_id, "HIGH_TEMPERATURE", now)

    if r.water_tank_level is not None:
        if r.water_tank_level < settings.MIN_TANK_LEVEL:
            sev = "CRITICAL" if r.water_tank_level < 5 else "WARNING"
            open_alert(db, device, "LOW_TANK", sev, f"Water tank for {name} is low ({r.water_tank_level:.0f}%).", now)
        else:
            resolve_alerts(db, device.device_id, "LOW_TANK", now)
