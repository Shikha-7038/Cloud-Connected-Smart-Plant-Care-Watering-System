"""Cloud database connection (SQLAlchemy).

DATABASE_URL decides where data lives:
  * local demo : sqlite:///./plant_care.db
  * cloud      : postgresql+psycopg2://...   (e.g. Supabase / Neon / RDS)
The application code is identical for both - that is the point of a managed DB.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings

_url = settings.DATABASE_URL
if _url.startswith("postgres://"):            # some providers still hand out this scheme
    _url = _url.replace("postgres://", "postgresql+psycopg2://", 1)

_kwargs = {"pool_pre_ping": True}
if _url.startswith("sqlite"):
    _kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(_url, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def init_db() -> None:
    from backend.models import tables  # noqa: F401  (register models)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
