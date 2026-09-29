"""Heartbeat monitoring: a device silent for too long is OFFLINE and raises a CRITICAL alert."""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.tables import Device
from backend.services.alert_service import open_alert
from cloud.database_service import SessionLocal

log = logging.getLogger("plantcare.offline")


def device_status(device: Device, now: datetime) -> str:
    if device.last_seen is None:
        return "offline"
    return "online" if (now - device.last_seen).total_seconds() <= settings.OFFLINE_AFTER_SECONDS else "offline"


def check_offline(db: Session, now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    count = 0
    for d in db.scalars(select(Device).where(Device.last_seen.is_not(None))).all():
        if device_status(d, now) == "offline":
            if open_alert(db, d, "DEVICE_OFFLINE", "CRITICAL",
                          f"No sensor data received from {d.device_id} during the expected interval.", now):
                count += 1
            if d.pump_on:                        # fail-safe: never leave the pump on for a silent device
                d.pump_on, d.pump_started_at = False, None
    db.commit()
    return count


def _run_once() -> int:
    with SessionLocal() as db:
        return check_offline(db)


async def offline_loop():
    while True:
        try:
            await asyncio.to_thread(_run_once)
        except Exception:                        # keep the monitor alive whatever happens
            log.exception("offline check failed")
        await asyncio.sleep(settings.OFFLINE_CHECK_INTERVAL)
