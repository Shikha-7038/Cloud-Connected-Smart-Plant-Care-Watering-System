"""Automated watering decision logic (pure functions -> easy to unit test).

Rules
-----
START when  auto-watering is ON
        AND soil_moisture < threshold
        AND water tank level >= minimum (if a tank sensor exists)
        AND the cooldown since the last watering has finished
        AND the pump is not already running.
STOP  when  soil_moisture >= target   (prevents overwatering)
        OR  the pump has run for max_watering_seconds (safety cut-off)
        OR  the tank runs low.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EngineConfig:
    max_watering_seconds: float = 30.0
    cooldown_seconds: float = 60.0
    min_tank_level: float = 10.0
    max_target: float = 95.0


@dataclass(frozen=True)
class Decision:
    action: str   # "START" | "STOP" | "NONE"
    reason: str


def target_moisture(threshold: float, margin: float, cfg: EngineConfig) -> float:
    """Moisture level at which the pump is switched off."""
    return min(threshold + margin, cfg.max_target)


def evaluate(*, soil: float, tank: float | None, threshold: float, target: float,
             auto_enabled: bool, pump_on: bool, pump_started_at: datetime | None,
             last_watering_end: datetime | None, now: datetime,
             cfg: EngineConfig) -> Decision:
    tank_low = tank is not None and tank < cfg.min_tank_level

    if pump_on:
        elapsed = (now - pump_started_at).total_seconds() if pump_started_at else 0.0
        if soil >= target:
            return Decision("STOP", "target_reached")
        if elapsed >= cfg.max_watering_seconds:
            return Decision("STOP", "max_duration")
        if tank_low:
            return Decision("STOP", "tank_low")
        return Decision("NONE", "watering_in_progress")

    if not auto_enabled:
        return Decision("NONE", "auto_disabled")
    if soil >= threshold:
        return Decision("NONE", "moisture_ok")
    if tank_low:
        return Decision("NONE", "tank_low")
    if last_watering_end and (now - last_watering_end).total_seconds() < cfg.cooldown_seconds:
        return Decision("NONE", "cooldown")
    return Decision("START", "below_threshold")
