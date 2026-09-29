# Cloud-Connected Smart Plant Care & Watering System

## Overview
A cloud-hosted platform that monitors soil moisture, temperature, humidity
and light for one or more plants, waters them automatically when needed,
and gives the owner a real-time dashboard, history, and alerts — with **no
physical hardware required**. A Python virtual sensor simulates realistic
plant behaviour, so the entire IoT-to-cloud pipeline can be built, tested
and demoed on a single laptop, then later handed off to a real ESP32
without changing the cloud architecture.

## Problem Statement
Manual watering is inconsistent — plants suffer from over- or
under-watering, and owners have no visibility into their plants' condition
when away from home.

## Objectives
- Continuously monitor soil moisture, temperature, humidity and light.
- Automate watering with configurable, plant-specific thresholds.
- Store history in a cloud database and expose it through a REST API.
- Provide a real-time dashboard with manual override and alerts.
- Detect offline devices and notify the owner.
- Demonstrate cloud-computing concepts (not just an embedded project).

## Features
Cloud-hosted app · simulated IoT sensor · cloud database · REST API ·
near-real-time dashboard · automated watering logic (with cooldown &
max-duration safety cutoffs) · historical storage & analytics · alerts
(low moisture / high temperature / low tank / offline) · JWT + API-key
security · automated tests · CI · optional real-hardware (ESP32) version.

## Industry Relevance
The same pattern (sensor → cloud → automation → dashboard) powers precision
farming, commercial greenhouses, nurseries, vertical farming, hydroponics,
smart homes, and campus/commercial landscaping. Business benefits: reduced
water wastage, remote monitoring, automated irrigation, historical
analytics, early alerts, and centralized management across many plants.

## Cloud Computing Concepts Demonstrated
See `docs/ARCHITECTURE.md` for a full mapping of SaaS/PaaS, serverless,
event-driven architecture, time-series data, REST, auth, secrets
management, scalability, and CI/CD to specific files in this repo.

## Architecture
See `docs/ARCHITECTURE.md` for the full data-flow diagram and database
schema.

## Technology Stack
- **Sensor:** Python virtual IoT simulator (`sensor_simulator/`)
- **Backend:** FastAPI (`backend/`)
- **Automation:** pure-Python rules engine (`automation/`)
- **Database:** SQLite locally / PostgreSQL in the cloud (`cloud/database_service.py`)
- **Frontend:** React + Vite (`frontend/`)
- **Auth:** JWT (users) + per-device API keys (`cloud/auth_service.py`)

## Sensor Simulation
`sensor_simulator/simulator.py` models a virtual plant: moisture falls
gradually (faster when hot), rises while the pump runs, temperature follows
a day curve, humidity moves opposite to temperature, and light follows a
day/night cycle. It posts JSON to the same endpoint a real ESP32 would use,
retries on network errors, and can simulate an outage (`--offline-after` /
`--offline-for`) to demonstrate store-and-forward buffering.

## Database Design
See `docs/ARCHITECTURE.md#database-schema`.

## REST APIs
| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/sensors/data` | Device ingests a reading (API key) |
| GET/POST | `/api/devices` | List / register devices |
| GET | `/api/devices/{id}` | Device detail + live status |
| GET | `/api/devices/{id}/latest` | Latest reading |
| GET | `/api/devices/{id}/history` | Historical readings |
| PUT | `/api/devices/{id}/threshold` | Update moisture threshold |
| PUT | `/api/devices/{id}/auto` | Toggle auto-watering |
| POST | `/api/devices/{id}/water` | Manual watering |
| GET | `/api/devices/{id}/watering-history` | Past watering events |
| GET | `/api/devices/{id}/analytics` | Aggregated stats |
| GET | `/api/alerts` / PUT `/api/alerts/{id}/acknowledge` | Alerts |

Full request/response/validation/status-code details are in the interactive
docs at `/docs` once the backend is running.

## Automated Watering
Configurable per-plant threshold + target margin, with a cooldown period and
a maximum-watering-duration safety cutoff to prevent overwatering or a
stuck-pump scenario. See `automation/watering_engine.py` and
`docs/ARCHITECTURE.md`.

## Plant Profiles
`automation/plant_profiles.py`: SUCCULENT (20%), TOMATO (40%), HERB (35%),
INDOOR (30%) — different plants hold water differently, so a succulent
watered at a tomato's threshold would rot.

## Dashboard
Live cards (moisture, temperature, humidity, light, pump status, plant
health), moisture/temperature/humidity history charts, watering history
table, manual "Water Now" button, auto-watering toggle, threshold editor,
and an alerts panel.

## Alerts
LOW_MOISTURE, HIGH_TEMPERATURE, LOW_TANK, DEVICE_OFFLINE — each with
INFO/WARNING/CRITICAL severity, stored in the database, shown on the
dashboard, auto-resolved when the condition clears.

## Device Monitoring
Heartbeat via `last_seen`; a device silent longer than
`OFFLINE_AFTER_SECONDS` is marked offline and raises a CRITICAL alert.

## Folder Structure
See `docs/FOLDER_STRUCTURE.md`.

## Installation
```bash
git clone https://github.com/<you>/Cloud-Connected-Smart-Plant-Care.git
cd Cloud-Connected-Smart-Plant-Care
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

## Environment Variables
See `.env.example` for the full list (database URL, JWT secret, watering
safety limits, offline-detection interval, simulator target, demo seed
credentials).

## Local Simulation (no hardware)
```bash
python scripts/seed_demo.py                        # creates demo user + 3 plants, prints an API key
uvicorn backend.app:app --reload --port 8000        # terminal 1
cd frontend && npm install && npm run dev           # terminal 2 (http://localhost:5173)
export DEVICE_API_KEY=<key from seed_demo.py>        # terminal 3
python -m sensor_simulator.simulator --fast
```
Or just run `./run_local.sh` (backend + simulator; run the frontend
separately). Log in with the credentials printed by the seed script, watch
moisture fall, cross the threshold, the virtual pump switch on, and the
chart/alerts update within a few seconds.

## Optional Hardware Setup
See `hardware/esp32_firmware.ino` and the wiring/BOM notes in
`docs/ARCHITECTURE.md` intro — swap the Python simulator for the ESP32 and
the cloud side needs no changes.

## Cloud Deployment
See `docs/DEPLOYMENT.md` (free-tier steps + enterprise-architecture mapping
across AWS/Azure/GCP).

## Testing
See `docs/TESTING.md`. Run with `pytest -v`.

## Security
See `docs/SECURITY.md`.

## Scalability
See `docs/ARCHITECTURE.md` and `reports/PROJECT_REPORT.md#scalability` for
how the design scales from 10 to 1,000,000+ readings using IoT brokers, API
gateways, serverless functions, time-series databases, and queues.

## Analytics
`GET /api/devices/{id}/analytics` returns average/min/max moisture,
average temperature/humidity, watering-event count, daily watering
frequency, estimated water used (ml), device uptime %, and plant health.

## Screenshots
See `docs/SCREENSHOT_CHECKLIST.md`.

## Results
The full simulated cycle (healthy → drying → threshold crossed → auto
watering → target reached → event logged → alert raised and resolved) runs
end-to-end locally in under two minutes with `--fast`, and is covered by
25 automated test scenarios (`docs/TESTING.md`).

## Limitations
- Free-tier cloud hosting can cold-start (a few seconds of latency after
  inactivity).
- The rate limiter is in-memory (per backend instance) — fine for one
  instance, but would need a shared store (e.g. Redis) behind a load
  balancer with multiple instances.
- The simulator models one plant's physics simply; it is not a substitute
  for real soil/sensor calibration.

## Future Improvements
Real ESP32 fleet + MQTT/IoT broker, weather-forecast-aware watering,
predictive watering via machine learning (see the optional AI model note
in `docs/ARCHITECTURE.md`), water-tank float-switch hardware, mobile push
notifications, multi-zone plants per node, solar-powered nodes, anomaly
detection.

## Learning Outcomes
End-to-end IoT-to-cloud architecture, REST API design & validation, cloud
database schema design & indexing, authentication/authorization, automated
decision-logic testing, alerting design, cloud deployment, and CI.

## Author
Built as a cloud computing course project.

## License
MIT — see `LICENSE`.
