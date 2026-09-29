"""Shared FastAPI dependencies: auth, ownership checks, rate limiting."""
import logging
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.tables import Device, User
from cloud.auth_service import decode_access_token
from cloud.database_service import get_db

log = logging.getLogger("plantcare.auth")

# Declaring this as a FastAPI security scheme (instead of reading the header
# manually) is what makes the "Authorize" button appear on /docs.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
                     db: Session = Depends(get_db)) -> User:
    if not creds or not creds.credentials:
        raise HTTPException(401, "Missing bearer token")
    user_id = decode_access_token(creds.credentials)
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user


def get_owned_device(device_id: str, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db)) -> Device:
    """Authorization: a user may only touch devices they own (404 hides other users' devices)."""
    device = db.get(Device, device_id)
    if not device or device.user_id != user.user_id:
        raise HTTPException(404, "Device not found")
    return device


class RateLimiter:
    """Tiny in-memory sliding-window limiter. In production use the API gateway / Redis."""

    def __init__(self):
        self.hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, limit: int, window: float = 60.0) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True

    def reset(self):
        self.hits.clear()


rate_limiter = RateLimiter()


def enforce_rate_limit(key: str):
    if not rate_limiter.check(key, settings.RATE_LIMIT_PER_MINUTE):
        log.warning("rate limit hit for %s", key)
        raise HTTPException(429, "Too many requests")


def api_key_header(x_api_key: str | None = Header(default=None)) -> str | None:
    return x_api_key