"""Test setup: use a throw-away SQLite DB and disable the background monitor."""
import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["ENABLE_OFFLINE_MONITOR"] = "false"
os.environ["JWT_SECRET"] = "test-secret"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app import app  # noqa: E402
from backend.utils.deps import rate_limiter  # noqa: E402
from cloud.database_service import Base, SessionLocal, engine  # noqa: E402


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine)
    from backend.models import tables  # noqa: F401
    Base.metadata.create_all(engine)
    rate_limiter.reset()
    with SessionLocal() as session:
        yield session


@pytest.fixture()
def client(db):
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/api/auth/register", json={"name": "Test", "email": "t@example.com", "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def device(client, auth):
    """A TOMATO device (threshold 40, target 60) plus its API key."""
    r = client.post("/api/devices", headers=auth, json={"device_id": "PLANT-001", "plant_name": "Tomato Plant",
                                                         "plant_type": "TOMATO", "location": "Balcony"})
    assert r.status_code == 201
    return {"id": "PLANT-001", "key": r.json()["api_key"]}


def reading(soil=55, temp=25, hum=60, light=70, tank=100, **extra):
    return {"device_id": "PLANT-001", "soil_moisture": soil, "temperature": temp,
            "humidity": hum, "light_level": light, "water_tank_level": tank, **extra}


@pytest.fixture()
def send(client, device):
    def _send(**kw):
        return client.post("/api/sensors/data", json=reading(**kw), headers={"x-api-key": device["key"]})
    return _send
