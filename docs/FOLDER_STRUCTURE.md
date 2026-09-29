# Project Folder Structure

```
Cloud-Connected-Smart-Plant-Care/
├── sensor_simulator/     Virtual IoT device — generates realistic readings, posts to the API
│   ├── simulator.py         VirtualPlant model + CloudClient (retry/back-off/offline buffering)
│   └── config.py            All simulator settings, from environment variables
│
├── backend/              Cloud backend (FastAPI)
│   ├── app.py               App entry point, CORS, lifespan (DB init + offline monitor)
│   ├── config.py            Environment-driven settings
│   ├── routes/               One file per resource: auth, sensors, devices, alerts
│   ├── models/               tables.py (SQLAlchemy) + schemas.py (Pydantic validation)
│   ├── services/              Business logic: reading pipeline, alerts, analytics, offline monitor
│   └── utils/deps.py          Shared FastAPI dependencies (auth, ownership, rate limiting)
│
├── automation/            Pure decision logic, framework-independent
│   ├── watering_engine.py    START/STOP rules, thresholds, cooldown, safety cutoffs
│   └── plant_profiles.py     Per-plant-type default thresholds
│
├── cloud/                 Cloud infrastructure glue
│   ├── database_service.py   SQLAlchemy engine/session (SQLite locally, Postgres in the cloud)
│   └── auth_service.py       Password hashing, JWT, API-key generation/verification
│
├── frontend/              React + Vite dashboard
│   └── src/                  components/, pages/, services/ (REST client)
│
├── hardware/              Optional real-hardware version
│   └── esp32_firmware.ino    Arduino/ESP32 code — same API, no cloud changes needed
│
├── scripts/
│   └── seed_demo.py           Creates a demo user + 3 demo plants
│
├── tests/                 Unit + integration tests (pytest)
├── sample_data/           Example sensor payload
├── docs/                  Architecture, deployment, security, testing, GitHub strategy
├── reports/               Project report, resume/LinkedIn text, interview prep
├── screenshots/           (empty — see docs/SCREENSHOT_CHECKLIST.md)
├── run_local.sh           One-command local demo (backend + simulator, no hardware)
├── requirements.txt / requirements-dev.txt
├── .env.example
└── .gitignore
```
