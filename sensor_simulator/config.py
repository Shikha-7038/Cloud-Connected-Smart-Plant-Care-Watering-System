"""Simulator settings (environment variables, with safe local-demo defaults)."""
import os

from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")
DEVICE_ID = os.getenv("DEVICE_ID", "PLANT-001")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "")            # printed by scripts/seed_demo.py
INTERVAL_SECONDS = float(os.getenv("SIM_INTERVAL_SECONDS", 2))

START_MOISTURE = float(os.getenv("SIM_START_MOISTURE", 55))
DRY_RATE = float(os.getenv("SIM_DRY_RATE", 0.8))            # % moisture lost per tick at 25°C
WATER_GAIN = float(os.getenv("SIM_WATER_GAIN", 5.0))        # % moisture gained per tick while pump ON
SIM_MINUTES_PER_TICK = float(os.getenv("SIM_MINUTES_PER_TICK", 10))   # speeds up the day/night cycle
START_HOUR = float(os.getenv("SIM_START_HOUR", 9))
TANK_DRAIN_PER_TICK = float(os.getenv("SIM_TANK_DRAIN", 0.8))         # tank % used per pumping tick

REQUEST_TIMEOUT = float(os.getenv("SIM_REQUEST_TIMEOUT", 5))
MAX_RETRIES = int(os.getenv("SIM_MAX_RETRIES", 3))
