# Cloud Security

| Concern | Implementation |
|---|---|
| User authentication | Email + password (PBKDF2-HMAC-SHA256, 200k iterations, random salt per user) → JWT access token |
| Device authentication | Per-device random API key; only its SHA-256 hash is stored, so a database leak cannot be used to impersonate a device |
| Authorization | Every device route depends on `get_owned_device`, which 404s (not 403) if the device belongs to someone else — this avoids confirming that a device ID exists at all |
| Transport security | HTTPS is required in production (enforced at the hosting platform / load balancer, since local `uvicorn --reload` is HTTP for development only) |
| Encryption at rest | Delegated to the managed database provider (Supabase/Render Postgres encrypt disks by default) |
| Secrets management | `JWT_SECRET`, `DATABASE_URL`, API keys all come from environment variables; `.env` is git-ignored; `backend/config.py` refuses to start in production with the default dev secret |
| Input validation | Every request body is a Pydantic model with explicit ranges (e.g. `soil_moisture: 0–100`) — malformed or out-of-range data is rejected with `422` before it reaches any business logic |
| Rate limiting | A per-device sliding-window limiter on the ingest endpoint (`backend/utils/deps.py`) — protects against a misbehaving or compromised device flooding the API. In production this belongs at the API gateway / load balancer layer as well |
| Device identity | Each physical/virtual device has its own `device_id` + API key, so one compromised key only exposes one plant, not the whole fleet |
| Logging & monitoring | Structured logs on every ingest, pump action, and alert; `/health` endpoint for uptime checks |
| Firmware security (real hardware) | Wi-Fi credentials and the API key should be stored in ESP32 NVS / a `secrets.h` excluded from version control, not hard-coded in a committed `.ino` file — the sample firmware inlines them only for teaching clarity |

## Why publicly exposing an IoT control endpoint is dangerous

The `/water` endpoint activates a physical pump. Without authentication, an
attacker could trigger it remotely (flooding a plant, wasting water, or — in
a home-automation context — worse, if the same pattern were reused for a
door lock or garage door). Without a cooldown and a maximum-duration
safety cutoff, even an *authenticated* bug (a stuck request, a retry storm)
could run a pump indefinitely and cause real physical damage — which is why
`automation/watering_engine.py` enforces both regardless of who or what
triggered the watering.
