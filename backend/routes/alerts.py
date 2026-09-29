"""GET /api/alerts, PUT /api/alerts/{id}/acknowledge"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.schemas import AlertOut
from backend.models.tables import Alert, Device, User
from backend.utils.deps import get_current_user
from cloud.database_service import get_db

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def list_alerts(status: str | None = Query(None, pattern="^(OPEN|ACKNOWLEDGED|RESOLVED)$"),
                limit: int = Query(50, ge=1, le=200),
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = select(Alert).join(Device, Device.device_id == Alert.device_id).where(Device.user_id == user.user_id)
    if status:
        q = q.where(Alert.status == status)
    return db.scalars(q.order_by(Alert.created_at.desc()).limit(limit)).all()


@router.put("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge(alert_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    dev = db.get(Device, alert.device_id) if alert else None
    if not alert or dev.user_id != user.user_id:
        raise HTTPException(404, "Alert not found")
    if alert.status == "OPEN":
        alert.status = "ACKNOWLEDGED"
        db.commit()
    return alert
