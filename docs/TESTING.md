# Testing Strategy

Run everything:

```bash
pip install -r requirements-dev.txt
pytest -v
```

`tests/test_watering_engine.py` and `tests/test_simulator.py` are pure unit
tests (no server, no I/O). `tests/test_api.py` uses FastAPI's `TestClient`
against a throw-away SQLite database created fresh for every test
(`tests/conftest.py`), so tests never touch your real `.env` database and
can run in CI with no external services.

| ID | Scenario | Input | Expected result |
|---|---|---|---|
| T01 | Sensor simulator starts | `python -m sensor_simulator.simulator --count 1` | Exits after one reading, no crash |
| T02 | Sensor reading generated | `VirtualPlant.step()` | All fields within documented ranges |
| T03 | Valid data reaches API | POST `/api/sensors/data` with a valid payload | `200`, `status: stored` |
| T04 | Invalid sensor data rejected | `soil_moisture=150` | `422` |
| T05 | Data stored in database | valid POST | Row appears in `sensor_readings` |
| T06 | Latest reading retrieved | GET `/latest` after 3 POSTs | Returns the most recent one |
| T07 | Historical readings retrieved | GET `/history` | Returns all 3, oldest → newest |
| T08 | Moisture above threshold | `soil=45`, threshold 40 | `pump: OFF` |
| T09 | Moisture below threshold | `soil=39`, threshold 40 | `pump: ON` |
| T10 | Automatic watering starts | as above | `WateringEvent` row created, `trigger_type=AUTO` |
| T11 | Moisture increases | simulator with `pump_on=True` | `moisture` rises tick over tick |
| T12 | Automatic watering stops | `soil` reaches target | `pump: OFF`, event `stop_reason=target_reached` |
| T13 | Cooldown prevents repeated watering | immediate low reading after stopping | `decision: cooldown`, no new event |
| T14 | Manual watering works | POST `/water` | `202`, pump turns on, blocked while already running |
| T15 | Alert generated | `soil` below threshold | `LOW_MOISTURE` alert, no duplicate on repeat reading |
| T16 | Alert acknowledged | PUT `/alerts/{id}/acknowledge` | status → `ACKNOWLEDGED`; auto-resolves when moisture recovers |
| T17 | Device offline detected | no reading for > `OFFLINE_AFTER_SECONDS` | `status: offline`, `DEVICE_OFFLINE` alert, pump forced off |
| T18 | Dashboard displays latest values | GET `/api/devices` | Includes `latest` reading + computed `plant_health` |
| T19 | Historical chart works | GET `/history?hours=24` | Time-ordered list the frontend feeds straight into Recharts |
| T20 | Database failure | simulated `OperationalError` | API returns `503`, not a stack trace |
| T21 | API failure (simulator side) | backend unreachable | Simulator retries with back-off, then buffers (store-and-forward) |
| T22 | Simulator retry | 500 from server | 3 attempts with exponential back-off before giving up on that reading |
| T23 | Unauthorized request | missing/garbage JWT or API key | `401` on every protected route |
| T24 | Threshold update | PUT `/threshold` | New value takes effect on the next reading |
| T25 | Multiple devices | two devices, one user | Each device's automation and data are fully isolated |

All 25 scenarios above are automated in `tests/test_api.py`,
`tests/test_watering_engine.py`, and `tests/test_simulator.py` (T01/T21/T22
are exercised through the simulator's CLI flags and retry logic rather than
pytest, since they involve real timing/network behaviour — see the
"offline mode" section of `README.md`).
