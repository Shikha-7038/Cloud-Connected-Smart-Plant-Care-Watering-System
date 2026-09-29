"""Virtual IoT plant node - behaves like an ESP32 with no hardware needed.

Realistic behaviour (not pure random):
  * soil moisture slowly falls (faster when hot) and jumps up while the pump is ON
  * temperature follows a day curve + slow drift, humidity moves opposite to it
  * light follows a day/night pattern
  * the cloud replies with the pump command ("ON"/"OFF"); the simulator obeys it
  * retries with back-off, logs API errors, and can simulate a network outage
    (readings are buffered and sent later = store-and-forward)

Usage (from project root):
  python -m sensor_simulator.simulator                      # run forever
  python -m sensor_simulator.simulator --count 60 --fast
  python -m sensor_simulator.simulator --offline-after 20 --offline-for 45
"""
import argparse
import logging
import math
import random
import time
from collections import deque
from datetime import datetime, timezone

import requests

from sensor_simulator import config as cfg

log = logging.getLogger("simulator")


class VirtualPlant:
    """Physics-lite model of one plant. `step()` advances one tick and returns a reading."""

    def __init__(self, device_id: str, seed: int | None = None):
        self.device_id = device_id
        self.rng = random.Random(seed)
        self.moisture = cfg.START_MOISTURE
        self.hour = cfg.START_HOUR
        self.temp_drift = 0.0
        self.hum_drift = 0.0
        self.tank = 100.0

    def step(self, pump_on: bool) -> dict:
        self.hour = (self.hour + cfg.SIM_MINUTES_PER_TICK / 60) % 24
        # temperature: day curve (coolest ~03:00, warmest ~15:00) + slow mean-reverting drift
        self.temp_drift = 0.9 * self.temp_drift + self.rng.gauss(0, 0.15)
        temp = 26 + 8 * math.sin(2 * math.pi * (self.hour - 9) / 24) + self.temp_drift
        temp = min(40.0, max(15.0, temp))
        # humidity moves opposite to temperature
        self.hum_drift = 0.9 * self.hum_drift + self.rng.gauss(0, 0.5)
        humidity = min(90.0, max(30.0, 62 - (temp - 26) * 2.2 + self.hum_drift))
        # light: 0 at night, peak at noon, small cloud noise
        sun = max(0.0, math.sin(math.pi * (self.hour - 6) / 12)) if 6 <= self.hour <= 18 else 0.0
        light = min(100.0, max(0.0, sun * 100 * self.rng.uniform(0.85, 1.0)))
        # soil moisture
        if pump_on and self.tank > 0:
            self.moisture += cfg.WATER_GAIN * self.rng.uniform(0.9, 1.1)
            self.tank = max(0.0, self.tank - cfg.TANK_DRAIN_PER_TICK)
        else:
            self.moisture -= cfg.DRY_RATE * (1 + (temp - 25) / 50) * self.rng.uniform(0.85, 1.15)
        self.moisture = min(100.0, max(0.0, self.moisture))
        return {"device_id": self.device_id,
                "soil_moisture": round(self.moisture, 1), "temperature": round(temp, 1),
                "humidity": round(humidity, 1), "light_level": round(light, 1),
                "water_tank_level": round(self.tank, 1),
                "timestamp": datetime.now(timezone.utc).isoformat()}


class CloudClient:
    def __init__(self, url: str, api_key: str):
        self.endpoint = url.rstrip("/") + "/api/sensors/data"
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    def send(self, payload: dict) -> dict | None:
        """POST with retries + exponential back-off. Returns the JSON reply or None if unreachable."""
        for attempt in range(1, cfg.MAX_RETRIES + 1):
            try:
                r = requests.post(self.endpoint, json=payload, headers=self.headers, timeout=cfg.REQUEST_TIMEOUT)
                if r.status_code == 200:
                    return r.json()
                if r.status_code in (400, 401, 404, 422):     # our fault - retrying will not help
                    log.error("API rejected reading (%s): %s", r.status_code, r.text[:200])
                    return {"status": "rejected", "pump": None}
                log.warning("API error %s (attempt %d/%d)", r.status_code, attempt, cfg.MAX_RETRIES)
            except requests.RequestException as e:
                log.warning("network error: %s (attempt %d/%d)", e.__class__.__name__, attempt, cfg.MAX_RETRIES)
            time.sleep(min(2 ** attempt * 0.25, 4))
        return None


def run(count: int, interval: float, offline_after: int, offline_for: float, seed: int | None) -> None:
    if not cfg.DEVICE_API_KEY:
        raise SystemExit("Set DEVICE_API_KEY (run `python scripts/seed_demo.py` to get one).")
    plant, client = VirtualPlant(cfg.DEVICE_ID, seed), CloudClient(cfg.API_URL, cfg.DEVICE_API_KEY)
    buffer: deque = deque(maxlen=500)          # store-and-forward queue
    pump_on, tick, offline_until = False, 0, 0.0
    log.info("Simulator started: %s -> %s every %.1fs", cfg.DEVICE_ID, cfg.API_URL, interval)

    while count == 0 or tick < count:
        tick += 1
        reading = plant.step(pump_on)
        if offline_after and tick == offline_after:
            offline_until = time.time() + offline_for
            log.warning("*** simulating network outage for %.0fs ***", offline_for)

        if time.time() < offline_until:                       # OFFLINE MODE: keep sensing, cannot send
            buffer.append(reading)
            log.info("[offline] buffered reading #%d (moisture=%.1f%%)", len(buffer), reading["soil_moisture"])
        else:
            buffer.append(reading)
            reply = None
            while buffer:                                     # flush oldest first
                reply = client.send(buffer[0])
                if reply is None:
                    log.warning("cloud unreachable, %d reading(s) kept in buffer", len(buffer))
                    break
                buffer.popleft()
            if reply and reply.get("pump") in ("ON", "OFF"):
                new_state = reply["pump"] == "ON"
                if new_state != pump_on:
                    log.info(">>> PUMP %s (cloud command)", reply["pump"])
                pump_on = new_state
            log.info("moisture=%5.1f%% temp=%4.1fC hum=%4.1f%% light=%5.1f%% tank=%5.1f%% pump=%s cloud=%s",
                     reading["soil_moisture"], reading["temperature"], reading["humidity"],
                     reading["light_level"], reading["water_tank_level"], "ON " if pump_on else "OFF",
                     (reply or {}).get("status", "unreachable"))
        time.sleep(interval)


def main() -> None:
    p = argparse.ArgumentParser(description="Virtual IoT plant sensor")
    p.add_argument("--count", type=int, default=0, help="number of readings (0 = forever)")
    p.add_argument("--interval", type=float, default=cfg.INTERVAL_SECONDS)
    p.add_argument("--fast", action="store_true", help="dry out 3x faster (quick demos)")
    p.add_argument("--offline-after", type=int, default=0, help="start an outage after N readings")
    p.add_argument("--offline-for", type=float, default=45, help="outage length in seconds")
    p.add_argument("--seed", type=int, default=None)
    a = p.parse_args()
    if a.fast:
        cfg.DRY_RATE *= 3
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        run(a.count, a.interval, a.offline_after, a.offline_for, a.seed)
    except KeyboardInterrupt:
        log.info("Simulator stopped")


if __name__ == "__main__":
    main()
