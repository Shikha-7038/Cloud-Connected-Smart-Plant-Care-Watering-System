"""Integration tests of the REST API + automation pipeline (FastAPI TestClient)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import OperationalError

from backend.models.tables import Alert
from backend.services.offline_monitor import check_offline
from tests.conftest import reading


# ---------- ingestion, validation, storage ----------
def test_valid_data_reaches_api_and_is_stored(client, auth, device, send):     # T03 T05
    r = send(soil=55)
    assert r.status_code == 200 and r.json()["status"] == "stored" and r.json()["pump"] == "OFF"
    assert client.get("/api/devices/PLANT-001/latest", headers=auth).json()["soil_moisture"] == 55


def test_invalid_sensor_data_rejected(send):                                   # T04
    assert send(soil=150).status_code == 422
    assert send(soil=-1).status_code == 422
    assert send(temp=500).status_code == 422
    assert send(hum="abc").status_code == 422


def test_future_timestamp_rejected(send):
    ts = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    assert send(timestamp=ts).status_code == 422


def test_duplicate_reading_ignored(client, auth, device, send):
    ts = datetime.now(timezone.utc).isoformat()
    assert send(timestamp=ts).json()["status"] == "stored"
    assert send(timestamp=ts).json()["status"] == "duplicate"
    assert len(client.get("/api/devices/PLANT-001/history", headers=auth).json()) == 1


def test_latest_and_history(client, auth, device, send):                        # T06 T07
    for s in (60, 58, 56):
        send(soil=s)
    hist = client.get("/api/devices/PLANT-001/history?limit=10", headers=auth).json()
    assert [h["soil_moisture"] for h in hist] == [60, 58, 56]                   # oldest -> newest
    assert client.get("/api/devices/PLANT-001/latest", headers=auth).json()["soil_moisture"] == 56


# ---------- automation ----------
def test_full_watering_cycle(client, auth, device, send):                       # T09-T12
    assert send(soil=55).json()["pump"] == "OFF"
    r = send(soil=39)                                                           # tomato threshold = 40
    assert r.json()["pump"] == "ON"
    assert send(soil=45).json()["pump"] == "ON"
    assert send(soil=61).json()["pump"] == "OFF"                                # target = 60
    events = client.get("/api/devices/PLANT-001/watering-history", headers=auth).json()
    assert len(events) == 1
    e = events[0]
    assert e["trigger_type"] == "AUTO" and e["moisture_before"] == 39 and e["moisture_after"] == 61
    assert e["stop_reason"] == "target_reached" and e["duration"] is not None


def test_cooldown_prevents_repeated_watering(client, auth, device, send):       # T13
    send(soil=39); send(soil=61)
    assert send(soil=30).json()["pump"] == "OFF"
    assert send(soil=30).json()["decision"] == "cooldown"
    assert len(client.get("/api/devices/PLANT-001/watering-history", headers=auth).json()) == 1


def test_auto_toggle_off_disables_watering(client, auth, device, send):
    client.put("/api/devices/PLANT-001/auto", headers=auth, json={"auto_watering": False})
    assert send(soil=10).json()["pump"] == "OFF"


def test_manual_watering(client, auth, device, send):                           # T14
    send(soil=45)
    r = client.post("/api/devices/PLANT-001/water", headers=auth)
    assert r.status_code == 202
    assert client.get("/api/devices/PLANT-001", headers=auth).json()["pump_on"] is True
    assert client.post("/api/devices/PLANT-001/water", headers=auth).status_code == 409   # already running
    assert send(soil=61).json()["pump"] == "OFF"
    ev = client.get("/api/devices/PLANT-001/watering-history", headers=auth).json()[0]
    assert ev["trigger_type"] == "MANUAL"


def test_manual_watering_blocked_when_soil_moist(client, auth, device, send):
    send(soil=90)
    assert client.post("/api/devices/PLANT-001/water", headers=auth).status_code == 409


def test_manual_watering_needs_data(client, auth, device):
    assert client.post("/api/devices/PLANT-001/water", headers=auth).status_code == 409


def test_threshold_update(client, auth, device, send):                          # T24
    r = client.put("/api/devices/PLANT-001/threshold", headers=auth, json={"moisture_threshold": 25})
    assert r.status_code == 200 and r.json()["moisture_threshold"] == 25
    assert send(soil=30).json()["pump"] == "OFF"                                # 30 >= 25 now fine
    assert client.put("/api/devices/PLANT-001/threshold", headers=auth, json={"moisture_threshold": 120}).status_code == 422


# ---------- alerts ----------
def test_alert_generated_acknowledged_and_resolved(client, auth, device, send):  # T15 T16
    send(soil=39)
    alerts = client.get("/api/alerts", headers=auth).json()
    low = [a for a in alerts if a["alert_type"] == "LOW_MOISTURE"]
    assert len(low) == 1 and low[0]["status"] == "OPEN" and "below 40%" in low[0]["message"]
    send(soil=38)
    assert len([a for a in client.get("/api/alerts", headers=auth).json() if a["alert_type"] == "LOW_MOISTURE"]) == 1  # no spam
    r = client.put(f"/api/alerts/{low[0]['alert_id']}/acknowledge", headers=auth)
    assert r.json()["status"] == "ACKNOWLEDGED"
    send(soil=61)                                                               # moisture recovers -> auto-resolved
    assert client.get("/api/alerts?status=RESOLVED", headers=auth).json()[0]["alert_type"] == "LOW_MOISTURE"


def test_high_temperature_and_low_tank_alerts(client, auth, device, send):
    send(soil=55, temp=39, tank=4)
    types = {a["alert_type"] for a in client.get("/api/alerts", headers=auth).json()}
    assert {"HIGH_TEMPERATURE", "LOW_TANK"} <= types


def test_device_offline_detected_and_cleared(client, auth, device, send, db):    # T17
    send(soil=55)
    assert client.get("/api/devices/PLANT-001", headers=auth).json()["status"] == "online"
    later = datetime.now(timezone.utc) + timedelta(seconds=600)
    assert check_offline(db, later) == 1
    offline = db.query(Alert).filter_by(alert_type="DEVICE_OFFLINE").one()
    assert offline.severity == "CRITICAL" and "PLANT-001" in offline.message
    assert check_offline(db, later) == 0                                        # no duplicate alert
    send(soil=55)                                                               # device is back
    assert db.query(Alert).filter_by(alert_type="DEVICE_OFFLINE").one().status == "RESOLVED" or True
    db.expire_all()
    assert db.query(Alert).filter_by(alert_type="DEVICE_OFFLINE").one().status == "RESOLVED"


# ---------- security ----------
def test_unauthorized_requests(client, device):                                 # T23
    assert client.get("/api/devices").status_code == 401
    assert client.get("/api/devices", headers={"Authorization": "Bearer garbage"}).status_code == 401
    assert client.post("/api/sensors/data", json=reading()).status_code == 401
    assert client.post("/api/sensors/data", json=reading(), headers={"x-api-key": "wrong"}).status_code == 401
    assert client.get("/api/alerts").status_code == 401


def test_users_cannot_access_other_users_devices(client, auth, device):
    other = client.post("/api/auth/register", json={"name": "B", "email": "b@example.com", "password": "password123"})
    h = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert client.get("/api/devices/PLANT-001", headers=h).status_code == 404
    assert client.post("/api/devices/PLANT-001/water", headers=h).status_code == 404
    assert client.get("/api/devices", headers=h).json() == []


def test_login_and_duplicate_registration(client, auth):
    assert client.post("/api/auth/login", json={"email": "t@example.com", "password": "password123"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "t@example.com", "password": "nope"}).status_code == 401
    assert client.post("/api/auth/register", json={"name": "T", "email": "t@example.com", "password": "password123"}).status_code == 409


# ---------- multiple devices, analytics ----------
def test_multiple_devices_isolated(client, auth, device, send):                 # T25
    r = client.post("/api/devices", headers=auth, json={"device_id": "PLANT-002", "plant_name": "Aloe", "plant_type": "SUCCULENT"})
    key2 = r.json()["api_key"]
    assert r.json()["moisture_threshold"] == 20
    client.post("/api/sensors/data", headers={"x-api-key": key2}, json=reading(soil=25, device_id="PLANT-002"))
    send(soil=39)
    devs = {d["device_id"]: d for d in client.get("/api/devices", headers=auth).json()}
    assert devs["PLANT-002"]["pump_on"] is False and devs["PLANT-001"]["pump_on"] is True   # 25>=20 fine, 39<40 waters
    assert client.post("/api/sensors/data", headers={"x-api-key": device["key"]},
                       json=reading(device_id="PLANT-002")).status_code == 401              # key of another device


def test_analytics(client, auth, device, send):
    for s in (55, 50, 39, 45, 61):
        send(soil=s)
    a = client.get("/api/devices/PLANT-001/analytics", headers=auth).json()
    assert a["readings"] == 5 and a["min_moisture"] == 39 and a["max_moisture"] == 61
    assert a["watering_events"] == 1 and a["plant_health"] == "Healthy"


# ---------- failure handling ----------
def test_database_failure_returns_503(client, auth, monkeypatch):               # T20
    from backend.routes import devices

    def boom(*a, **k):
        raise OperationalError("SELECT", {}, Exception("db down"))
    monkeypatch.setattr(devices, "device_dict", boom)
    assert client.get("/api/devices", headers=auth).status_code in (200, 503)      # empty list never hits device_dict
    client.post("/api/devices", headers=auth, json={"device_id": "X1", "plant_name": "x"})
    r = client.get("/api/devices", headers=auth)
    assert r.status_code == 503 and "unavailable" in r.json()["detail"]


def test_rate_limit(client, device, send, monkeypatch):
    from backend.config import settings
    monkeypatch.setattr(settings, "RATE_LIMIT_PER_MINUTE", 3)
    codes = [send(soil=55 - i).status_code for i in range(5)]
    assert codes[:3] == [200, 200, 200] and 429 in codes[3:]
