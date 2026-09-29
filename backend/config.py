"""Central configuration. Everything comes from environment variables (.env)."""
import os

from dotenv import load_dotenv

load_dotenv()


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, default))


class Settings:
    ENV = os.getenv("APP_ENV", "development")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./plant_care.db")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-only-secret-change-me")
    JWT_EXPIRE_MINUTES = int(_f("JWT_EXPIRE_MINUTES", 720))
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

    # watering safety rules
    MAX_WATERING_SECONDS = _f("MAX_WATERING_SECONDS", 30)
    COOLDOWN_SECONDS = _f("COOLDOWN_SECONDS", 60)
    MIN_TANK_LEVEL = _f("MIN_TANK_LEVEL", 10)
    PUMP_FLOW_ML_PER_SEC = _f("PUMP_FLOW_ML_PER_SEC", 8)

    # monitoring
    EXPECTED_INTERVAL_SECONDS = _f("EXPECTED_INTERVAL_SECONDS", 2)   # how often a device reports
    OFFLINE_AFTER_SECONDS = _f("OFFLINE_AFTER_SECONDS", 30)
    OFFLINE_CHECK_INTERVAL = _f("OFFLINE_CHECK_INTERVAL", 10)
    ENABLE_OFFLINE_MONITOR = os.getenv("ENABLE_OFFLINE_MONITOR", "true").lower() == "true"
    RATE_LIMIT_PER_MINUTE = int(_f("RATE_LIMIT_PER_MINUTE", 120))


settings = Settings()

if settings.ENV == "production" and settings.JWT_SECRET == "dev-only-secret-change-me":
    raise RuntimeError("Set a strong JWT_SECRET before running in production")
