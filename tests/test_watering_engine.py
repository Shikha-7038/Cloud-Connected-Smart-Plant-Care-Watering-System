"""Pure unit tests of the watering rules (no server, no database)."""
from datetime import datetime, timedelta, timezone

from automation.plant_profiles import get_profile, normalize_type
from automation.watering_engine import EngineConfig, evaluate, target_moisture

NOW = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
CFG = EngineConfig(max_watering_seconds=30, cooldown_seconds=60, min_tank_level=10)


def run(**over):
    base = dict(soil=50, tank=100, threshold=30, target=50, auto_enabled=True, pump_on=False,
                pump_started_at=None, last_watering_end=None, now=NOW, cfg=CFG)
    base.update(over)
    return evaluate(**base)


def test_moisture_above_threshold_no_watering():                      # T08
    assert run(soil=45).action == "NONE"


def test_moisture_below_threshold_starts_watering():                  # T09/T10
    d = run(soil=29)
    assert (d.action, d.reason) == ("START", "below_threshold")


def test_exactly_at_threshold_does_not_start():
    assert run(soil=30).action == "NONE"


def test_pump_stops_at_target():                                      # T12
    d = run(soil=51, pump_on=True, pump_started_at=NOW - timedelta(seconds=5))
    assert (d.action, d.reason) == ("STOP", "target_reached")


def test_pump_keeps_running_until_target():
    assert run(soil=40, pump_on=True, pump_started_at=NOW - timedelta(seconds=5)).action == "NONE"


def test_max_duration_cutoff_prevents_continuous_watering():
    d = run(soil=35, pump_on=True, pump_started_at=NOW - timedelta(seconds=31))
    assert (d.action, d.reason) == ("STOP", "max_duration")


def test_cooldown_prevents_repeated_activation():                     # T13
    d = run(soil=20, last_watering_end=NOW - timedelta(seconds=10))
    assert (d.action, d.reason) == ("NONE", "cooldown")


def test_watering_allowed_after_cooldown():
    assert run(soil=20, last_watering_end=NOW - timedelta(seconds=61)).action == "START"


def test_low_tank_blocks_watering():
    assert run(soil=20, tank=5).reason == "tank_low"


def test_low_tank_stops_running_pump():
    d = run(soil=20, tank=5, pump_on=True, pump_started_at=NOW)
    assert (d.action, d.reason) == ("STOP", "tank_low")


def test_auto_disabled_never_starts():
    assert run(soil=5, auto_enabled=False).reason == "auto_disabled"


def test_plant_profiles():
    assert get_profile("succulent")["threshold"] == 20
    assert get_profile("Tomato")["threshold"] == 40
    assert get_profile("herb")["threshold"] == 35
    assert normalize_type("indoor plant") == "INDOOR"
    assert normalize_type("cactus?") == "INDOOR"       # unknown -> safe default


def test_target_capped():
    assert target_moisture(90, 20, CFG) == 95
