"""Authentication helpers: password hashing, JWT for users, API keys for devices."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from backend.config import settings


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return hmac.compare_digest(check, digest)


def create_access_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": user_id, "exp": exp}, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> str | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"]).get("sub")
    except jwt.PyJWTError:
        return None


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """Only the hash is stored, so a database leak does not leak device keys."""
    return hashlib.sha256(key.encode()).hexdigest()


def verify_api_key(key: str | None, stored_hash: str) -> bool:
    return bool(key) and hmac.compare_digest(hash_api_key(key), stored_hash)
