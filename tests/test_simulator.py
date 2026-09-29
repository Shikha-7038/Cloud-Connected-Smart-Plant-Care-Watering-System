"""Simulator behaviour tests (no network needed)."""
from sensor_simulator.simulator import VirtualPlant


def test_reading_generated_and_in_range():                            # T02
    p = VirtualPlant("PLANT-001", seed=1)
    for _ in range(300):
        r = p.step(pump_on=False)
        assert 0 <= r["soil_moisture"] <= 100
        assert 15 <= r["temperature"] <= 40
        assert 30 <= r["humidity"] <= 90
        assert 0 <= r["light_level"] <= 100
        assert r["device_id"] == "PLANT-001" and "timestamp" in r


def test_moisture_decreases_then_increases_when_watered():           # T11
    p = VirtualPlant("PLANT-001", seed=2)
    start = p.moisture
    for _ in range(10):
        p.step(pump_on=False)
    dried = p.moisture
    assert dried < start
    for _ in range(4):
        p.step(pump_on=True)
    assert p.moisture > dried


def test_light_follows_day_night():
    p = VirtualPlant("PLANT-001", seed=3)
    lights = {}
    for _ in range(200):
        r = p.step(False)
        lights[round(p.hour)] = r["light_level"]
    assert lights[0] == 0 and lights[12] > 50


def test_values_change_gradually_not_random():
    p = VirtualPlant("PLANT-001", seed=4)
    prev = p.step(False)
    for _ in range(100):
        cur = p.step(False)
        assert abs(cur["temperature"] - prev["temperature"]) < 2
        assert abs(cur["soil_moisture"] - prev["soil_moisture"]) < 2
        prev = cur
