"""Device management, history, threshold, auto-mode, manual watering, analytics."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from automation.plant_profiles import get_profile, normalize_type
from backend.config import settings
from backend.models.schemas import (AutoIn, DeviceIn, ReadingOut, ThresholdIn, WateringEventOut)
from backend.models.tables import Device, SensorReading, User, WateringEvent
from backend.services.analytics_service import compute_analytics, health_status
from backend.services.offline_monitor import device_status
from backend.services.reading_service import latest_reading, start_manual_watering, target_for
from backend.utils.deps import get_current_user, get_owned_device
from cloud.auth_service import generate_api_key, hash_api_key
from cloud.database_service import get_db

router = APIRouter(prefix="/api/devices", tags=["devices"])


def _now():
    return datetime.now(timezone.utc)


def device_dict(db: Session, d: Device) -> dict:
    latest = latest_reading(db, d.device_id)
    return {"device_id": d.device_id, "plant_name": d.plant_name, "plant_type": d.plant_type,
            "location": d.location, "moisture_threshold": d.moisture_threshold,
            "target_moisture": target_for(d), "auto_watering": d.auto_watering,
            "pump_on": d.pump_on, "status": device_status(d, _now()),
            "plant_health": health_status(d, latest.soil_moisture if latest else None),
            "last_seen": d.last_seen, "last_watered_at": d.last_watered_at,
            "created_at": d.created_at,
            "latest": ReadingOut.model_validate(latest) if latest else None}


@router.get("")
def list_devices(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Device).where(Device.user_id == user.user_id).order_by(Device.created_at)).all()
    return [device_dict(db, d) for d in rows]


@router.post("", status_code=201)
def create_device(body: DeviceIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ptype = normalize_type(body.plant_type)
    threshold = body.moisture_threshold if body.moisture_threshold is not None else get_profile(ptype)["threshold"]
    api_key = generate_api_key()
    dev = Device(device_id=body.device_id, user_id=user.user_id, plant_name=body.plant_name,
                 plant_type=ptype, location=body.location, moisture_threshold=threshold,
                 api_key_hash=hash_api_key(api_key))
    db.add(dev)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Device ID already exists")
    # the raw key is shown ONCE; only its hash is stored
    return {**device_dict(db, dev), "api_key": api_key}


@router.get("/{device_id}")
def get_device(dev: Device = Depends(get_owned_device), db: Session = Depends(get_db)):
    return device_dict(db, dev)


@router.get("/{device_id}/latest", response_model=ReadingOut)
def get_latest(dev: Device = Depends(get_owned_device), db: Session = Depends(get_db)):
    r = latest_reading(db, dev.device_id)
    if not r:
        raise HTTPException(404, "No readings yet")
    return r


@router.get("/{device_id}/history", response_model=list[ReadingOut])
def get_history(limit: int = Query(100, ge=1, le=1000), hours: int | None = Query(None, ge=1, le=720),
                dev: Device = Depends(get_owned_device), db: Session = Depends(get_db)):
    q = select(SensorReading).where(SensorReading.device_id == dev.device_id)
    if hours:
        q = q.where(SensorReading.timestamp >= _now() - timedelta(hours=hours))
    rows = db.scalars(q.order_by(SensorReading.timestamp.desc()).limit(limit)).all()
    return list(reversed(rows))                      # oldest -> newest for charts


@router.put("/{device_id}/threshold")
def set_threshold(body: ThresholdIn, dev: Device = Depends(get_owned_device), db: Session = Depends(get_db)):
    dev.moisture_threshold = body.moisture_threshold
    db.commit()
    return device_dict(db, dev)


@router.put("/{device_id}/auto")
def set_auto(body: AutoIn, dev: Device = Depends(get_owned_device), db: Session = Depends(get_db)):
    dev.auto_watering = body.auto_watering
    db.commit()
    return device_dict(db, dev)


@router.post("/{device_id}/water", status_code=202)
def water_now(dev: Device = Depends(get_owned_device), db: Session = Depends(get_db)):
    try:
        ev = start_manual_watering(db, dev, _now())
    except PermissionError as e:
        raise HTTPException(409, str(e))
    return {"message": "Manual watering started", "event_id": ev.event_id, "pump": "ON"}


@router.get("/{device_id}/watering-history", response_model=list[WateringEventOut])
def watering_history(limit: int = Query(50, ge=1, le=500), dev: Device = Depends(get_owned_device),
                     db: Session = Depends(get_db)):
    return db.scalars(select(WateringEvent).where(WateringEvent.device_id == dev.device_id)
                      .order_by(WateringEvent.timestamp.desc()).limit(limit)).all()


@router.get("/{device_id}/analytics")
def analytics(hours: int = Query(24, ge=1, le=720), dev: Device = Depends(get_owned_device),
              db: Session = Depends(get_db)):
    return compute_analytics(db, dev, hours, _now(), settings.EXPECTED_INTERVAL_SECONDS)
