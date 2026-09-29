"""Create a demo user and three demo plants (local/demo use only).

  python scripts/seed_demo.py

Credentials come from env vars (see .env.example); the defaults below are for a
throw-away LOCAL demo only - never use them on a public deployment.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select  # noqa: E402

from automation.plant_profiles import get_profile  # noqa: E402
from backend.models.tables import Device, User  # noqa: E402
from cloud.auth_service import hash_api_key, hash_password  # noqa: E402
from cloud.database_service import SessionLocal, init_db  # noqa: E402

EMAIL = os.getenv("DEMO_EMAIL", "demo@example.com")
PASSWORD = os.getenv("DEMO_PASSWORD", "demo12345")
DEVICE_KEY = os.getenv("DEMO_DEVICE_API_KEY", "demo-device-key")
PLANTS = [("PLANT-001", "Tomato Plant", "TOMATO", "Balcony"),
          ("PLANT-002", "Aloe Vera", "SUCCULENT", "Living room"),
          ("PLANT-003", "Basil", "HERB", "Kitchen")]


def main() -> None:
    init_db()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == EMAIL))
        if not user:
            user = User(name="Demo User", email=EMAIL, password_hash=hash_password(PASSWORD))
            db.add(user)
            db.flush()
        for did, name, ptype, loc in PLANTS:
            if not db.get(Device, did):
                db.add(Device(device_id=did, user_id=user.user_id, plant_name=name, plant_type=ptype,
                              location=loc, moisture_threshold=get_profile(ptype)["threshold"],
                              api_key_hash=hash_api_key(DEVICE_KEY)))
        db.commit()
    print(f"Demo user : {EMAIL} / {PASSWORD}")
    print(f"Devices   : {', '.join(p[0] for p in PLANTS)}")
    print(f"Device key: {DEVICE_KEY}   (export DEVICE_API_KEY={DEVICE_KEY})")


if __name__ == "__main__":
    main()
