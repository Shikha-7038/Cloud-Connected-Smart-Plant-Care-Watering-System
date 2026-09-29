# Project Report — Cloud-Connected Smart Plant Care & Watering System

## Abstract
This project implements a cloud-connected IoT platform for automated plant
care. Soil moisture, temperature, humidity and light readings — generated
by a realistic Python virtual sensor (with an optional real ESP32 path) —
are ingested through a REST API, stored in a cloud database, evaluated by
an automated watering engine, and surfaced through a real-time React
dashboard with alerting and historical analytics. The project demonstrates
end-to-end cloud-computing skills: API design, authentication and
authorization, database design, event-driven automation, monitoring, and
cloud deployment.

## Introduction
Home and small-scale commercial plant care is typically manual and
error-prone. This project applies IoT-to-cloud patterns — the same ones
used in commercial precision agriculture — at a scale and cost accessible
to a student with no physical hardware budget.

## Problem Statement
Without continuous monitoring, soil moisture drifts outside a plant's safe
range between manual checks, causing stress, wilting, or root rot, and the
owner has no way to check on or water plants remotely.

## Objectives
1. Ingest sensor data over a secured REST API.
2. Persist readings and derived events in a cloud database.
3. Apply configurable, plant-specific automated watering rules with
   overwatering safeguards.
4. Provide real-time visibility and manual control through a dashboard.
5. Alert the owner to abnormal conditions or device silence.
6. Demonstrate the project is cloud-oriented, testable, and deployable.

## Existing System
Traditional approaches are either fully manual (a person checks soil by
hand) or use isolated hardware timers with no data logging, no remote
visibility, and no adaptive thresholds per plant type.

## Proposed System
A layered architecture — sensor/simulator → REST API → cloud database →
automation engine → dashboard — where any layer can be swapped
independently (e.g. simulator → real ESP32, SQLite → managed Postgres)
without touching the others.

## Industry Relevance
Smart agriculture, precision farming, commercial greenhouses and nurseries,
vertical farming/hydroponics, smart homes, and campus/commercial
landscaping all use this sensor-to-cloud-to-automation pattern, primarily
for reduced water waste, remote monitoring, and data-driven care decisions.

## Cloud Computing Concepts
Detailed mapping of SaaS/PaaS, serverless computing, event-driven
architecture, REST, time-series data, authentication/authorization,
secrets management, logging/monitoring, and CI/CD to this codebase is in
`docs/ARCHITECTURE.md`.

## IoT Concepts
Device identity (API key per device), heartbeat/offline detection,
store-and-forward buffering during connectivity loss, and a documented
path to MQTT for a broker-based real-hardware fleet
(`docs/DEPLOYMENT.md`).

## Technology Stack
Python 3.12, FastAPI, SQLAlchemy, Pydantic, PyJWT, SQLite/PostgreSQL,
React 18 + Vite, Recharts, pytest.

## Architecture
See `docs/ARCHITECTURE.md`.

## Sensor Simulation
A physics-lite model (`sensor_simulator/simulator.py`) with gradual trends
rather than pure randomness: moisture falls faster when hot and rises while
watering; temperature follows a day curve with slow drift; light follows a
day/night cycle. Includes retry with back-off and an offline/store-and-
forward mode.

## Database Design
Five tables — `users`, `devices`, `sensor_readings`, `watering_events`,
`alerts` — normalized around one user owning many devices, each producing
many readings, watering events, and alerts. See
`docs/ARCHITECTURE.md#database-schema` for the full schema and indexing
rationale.

## REST API
Ten endpoints covering ingestion, device management, history, threshold
and auto-mode control, manual watering, watering history, analytics, and
alert acknowledgement — documented interactively via FastAPI's `/docs`.

## Watering Algorithm
Threshold-based START, target-based STOP, with a cooldown period and a
maximum-watering-duration cutoff to prevent rapid re-triggering or a
stuck-open pump. See `automation/watering_engine.py`.

## Dashboard
React + Vite single-page app: live stat cards, three time-series charts
(moisture/temperature/humidity), a watering-history table, an alerts panel,
manual watering, auto-watering toggle, and threshold editing.

## Alerts
Four alert types with three severities, auto-opened and auto-resolved based
on the newest reading, with duplicate-suppression so a sustained condition
raises one alert, not one per reading.

## Device Monitoring
A background task periodically checks each device's `last_seen` timestamp
against a configurable interval and raises a CRITICAL `DEVICE_OFFLINE`
alert (and fails the pump safely off) if the device has gone silent.

## Cloud Deployment
Free-tier path (Vercel + Render/Railway + Supabase) and an enterprise-style
serverless architecture mapped across AWS/Azure/GCP — see
`docs/DEPLOYMENT.md`.

## Testing
25 documented test scenarios covering ingestion, validation, automation,
alerts, offline detection, security, and failure handling, implemented as
automated pytest tests. See `docs/TESTING.md`.

## Security
Password hashing (PBKDF2), JWT auth, hashed per-device API keys, ownership
checks (404 rather than 403 to avoid leaking existence), Pydantic input
validation, rate limiting, and secrets kept out of source control. See
`docs/SECURITY.md`.

## Scalability
### 10 plants
A single small backend instance and the free-tier database handle this
comfortably; no architectural changes needed.

### 1,000 plants
Add an index-aware query pattern (already in place), consider connection
pooling limits on the managed database, and keep the rate limiter
per-device so no single plant can starve the others.

### 100,000 plants
Move ingestion behind an API gateway with autoscaling backend instances
(stateless FastAPI workers scale horizontally without code changes),
introduce a message queue between ingestion and the automation engine so a
burst of readings doesn't block request threads, and move the rate limiter
to a shared store (Redis) since in-memory counters no longer coordinate
across instances.

### 1,000,000 sensor readings
Migrate `sensor_readings` to a genuinely time-series-oriented store
(Timestream / TimescaleDB) with data-retention/rollup policies (e.g. keep
raw data for 30 days, hourly aggregates thereafter), and serve
"latest reading" from a fast key-value cache rather than querying the full
history table.

### Thousands of devices reporting simultaneously
A single-process backend would exhaust its connection pool and CPU under a
synchronized burst (e.g. all devices reporting on the same minute mark).
The mitigation is the same pattern used across the scaling steps above:
an API gateway to absorb bursts, a queue to decouple ingestion from
processing, autoscaling stateless workers, and a database sized/sharded
for the write volume.

## Analytics
Average/min/max moisture, average temperature/humidity, watering-event
count, daily watering frequency, estimated water usage (from pump run-time
× flow rate), device uptime percentage, and current plant health status —
computed on demand from stored readings and events.

## Results
The complete pipeline — realistic drying, threshold crossing, automated
watering, target-reached shutoff, event logging, and alert
raise/auto-resolve — was verified end-to-end via the simulator's `--fast`
mode and via 25 automated pytest scenarios covering the same behaviour
under test isolation.

## Advantages
No hardware required to build or demonstrate the full system; the same
architecture accepts real ESP32 hardware without modification; clear
separation between pure decision logic (`automation/`) and I/O (`backend/`,
`cloud/`) keeps the core rules easy to test and reason about.

## Limitations
Free-tier hosting cold-starts; the in-memory rate limiter does not
coordinate across multiple backend instances; the simulator's plant model
is a simplified approximation, not a calibrated agronomic model.

## Future Scope
Real ESP32 fleet over MQTT, weather-aware watering, ML-based predictive
watering (feature sketch in the original design notes), tank float-switch
hardware, mobile push notifications, multi-zone/multi-plant nodes,
solar-powered nodes, anomaly detection on sensor streams.

## Conclusion
The system meets all fourteen required capabilities — cloud-hosted app,
simulated IoT data, cloud database, REST communication, near-real-time
dashboard, automated watering, historical storage, alerts, remote
monitoring, cloud deployment, security, scalability, testing, and
GitHub-ready proof of work — while remaining fully executable without any
physical hardware.
