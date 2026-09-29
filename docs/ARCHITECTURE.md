# Architecture

## Data flow

```
Virtual Plant (Python simulator)  or  ESP32 + real sensors
            │  HTTPS  POST /api/sensors/data   (x-api-key)
            ▼
      FastAPI Backend  ── validates payload (Pydantic)
            │
            ├── stores reading ────────► Cloud Database (SQLite / PostgreSQL)
            ├── Automation Engine ──────► decides START/STOP watering
            ├── Alert Service ──────────► LOW_MOISTURE / HIGH_TEMPERATURE / LOW_TANK
            └── replies { pump: "ON"|"OFF" } to the device
            ▼
     React Dashboard  ── polls REST API (JWT auth) ── charts, manual water, thresholds
            ▼
          User
```

A background task (`offline_monitor.py`) runs on a timer inside the same
backend process and marks a device OFFLINE (+ alert) if no reading has
arrived within `OFFLINE_AFTER_SECONDS` — the cloud equivalent of a heartbeat.

## Why this counts as "cloud computing", not just an Arduino project

| Concept | Where it lives |
|---|---|
| SaaS | The React dashboard — a hosted app the user just opens in a browser |
| PaaS | FastAPI deployed on Render/Railway — you ship code, the platform runs it |
| IaaS (equivalent) | The managed Postgres instance (Supabase/Neon) — you don't manage the VM |
| Serverless / Functions | The advanced deployment option (`docs/DEPLOYMENT.md` §Option B) using AWS Lambda / Cloud Functions |
| Event-driven architecture | Sensor POST → automation decision → alert → dashboard refresh, each step reacting to the previous event |
| REST API | `backend/routes/*.py` — resource-based endpoints, standard verbs & status codes |
| Time-series data | `sensor_readings` table, indexed on `(device_id, timestamp)` |
| Authentication / Authorization | JWT for users (`cloud/auth_service.py`), per-device API keys, ownership checks in `get_owned_device` |
| Secrets management | Everything sensitive comes from environment variables (`.env`, never committed) |
| Scalability / Elasticity | Stateless backend (any instance can serve any request) → horizontal autoscaling behind a load balancer |
| Monitoring / Logging | Structured `logging` throughout; `/health` endpoint for uptime checks |
| CI/CD | `.github/workflows/ci.yml` runs tests + frontend build on every push |

## Database schema

```
users (user_id PK, name, email UNIQUE, password_hash, created_at)
   │ 1
   │
   │ N
devices (device_id PK, user_id FK, plant_name, plant_type, location,
         moisture_threshold, auto_watering, api_key_hash,
         last_seen, pump_on, pump_started_at, last_watering_end, last_watered_at)
   │ 1
   ├── N sensor_readings (reading_id PK, device_id FK, soil_moisture, temperature,
   │                      humidity, light_level, water_tank_level, timestamp,
   │                      UNIQUE(device_id, timestamp), INDEX(device_id, timestamp))
   ├── N watering_events (event_id PK, device_id FK, trigger_type, moisture_before,
   │                      moisture_after, duration, stop_reason, timestamp, ended_at)
   └── N alerts (alert_id PK, device_id FK, alert_type, severity, message, status,
                 created_at, resolved_at)
```

- **Indexing:** `(device_id, timestamp)` on `sensor_readings` makes "latest
  reading" and "history for device X" queries fast even with millions of rows.
  The `UNIQUE` constraint on the same pair gives duplicate-reading rejection
  for free (a network retry that resends the same payload is a no-op).
- **Relationships:** one user → many devices → many readings / watering
  events / alerts. Deleting a user's device (not implemented in the MVP UI,
  but trivial to add) should cascade or archive the child rows.

## Automation engine

`automation/watering_engine.py` is a small set of pure functions with no
database or network dependency, so it is unit-tested directly (see
`tests/test_watering_engine.py`). It is deliberately kept separate from
`backend/services/reading_service.py`, which is the "glue" that calls the
engine and persists the result — this separation is what makes the rules
testable without spinning up a server.
