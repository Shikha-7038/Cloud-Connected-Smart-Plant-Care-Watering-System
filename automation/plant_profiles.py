"""Plant profiles: different plants need different watering rules.

A succulent stores water and rots if kept wet; a tomato is thirsty and stresses
quickly when dry. Each profile gives a default moisture threshold (start
watering below it), a target margin (stop watering at threshold + margin) and a
maximum comfortable air temperature (used by the HIGH_TEMPERATURE alert).
"""

PROFILES = {
    "SUCCULENT": {"threshold": 20, "target_margin": 15, "max_temp": 38.0},
    "TOMATO": {"threshold": 40, "target_margin": 20, "max_temp": 35.0},
    "HERB": {"threshold": 35, "target_margin": 20, "max_temp": 32.0},
    "INDOOR": {"threshold": 30, "target_margin": 20, "max_temp": 32.0},
}
DEFAULT_PROFILE = "INDOOR"


def normalize_type(plant_type: str | None) -> str:
    key = (plant_type or DEFAULT_PROFILE).strip().upper().replace(" ", "_")
    if key == "INDOOR_PLANT":
        key = "INDOOR"
    return key if key in PROFILES else DEFAULT_PROFILE


def get_profile(plant_type: str | None) -> dict:
    return PROFILES[normalize_type(plant_type)]
