#!/usr/bin/env bash
# One-command local demo: backend + seed data + simulator, no hardware needed.
set -e
python -m venv .venv 2>/dev/null || true
source .venv/bin/activate
pip install -r requirements-dev.txt
cp -n .env.example .env || true

echo "Seeding demo user + devices..."
python scripts/seed_demo.py

echo "Starting backend on http://localhost:8000 (docs at /docs) ..."
uvicorn backend.app:app --reload --port 8000 &
BACKEND_PID=$!
trap "kill $BACKEND_PID" EXIT
sleep 2

echo "Starting sensor simulator (Ctrl+C to stop everything)..."
export DEVICE_API_KEY="${DEMO_DEVICE_API_KEY:-demo-device-key}"
python -m sensor_simulator.simulator --fast
