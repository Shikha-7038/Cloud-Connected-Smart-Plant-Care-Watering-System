"""POST /api/sensors/data  - the IoT ingestion endpoint (device API-key protected)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.models.schemas import SensorIn
from backend.models.tables import Device
from backend.services.reading_service import process_reading
from backend.utils.deps import api_key_header, enforce_rate_limit
from cloud.auth_service import verify_api_key
from cloud.database_service import get_db

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.post("/data")
def ingest(body: SensorIn, api_key: str | None = Depends(api_key_header), db: Session = Depends(get_db)):
    device = db.get(Device, body.device_id)
    # same 401 for "unknown device" and "bad key" so attackers cannot enumerate device IDs
    if not device or not verify_api_key(api_key, device.api_key_hash):
        raise HTTPException(401, "Invalid device credentials")
    enforce_rate_limit(f"ingest:{device.device_id}")
    try:
        return process_reading(db, device, body, datetime.now(timezone.utc))
    except ValueError as e:
        raise HTTPException(422, str(e))
