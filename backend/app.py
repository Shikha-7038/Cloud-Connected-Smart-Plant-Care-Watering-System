"""FastAPI application entry point.

Run from the project root:  uvicorn backend.app:app --reload --port 8000
Interactive API docs:       http://localhost:8000/docs
"""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.config import settings
from backend.routes import alerts, auth, devices, sensors
from backend.services.offline_monitor import offline_loop
from cloud.database_service import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("plantcare")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(offline_loop()) if settings.ENABLE_OFFLINE_MONITOR else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Cloud-Connected Smart Plant Care API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])

for r in (auth.router, sensors.router, devices.router, alerts.router):
    app.include_router(r)


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):
    """Graceful degradation: a database outage returns 503 (devices will retry), not a crash."""
    log.error("database error on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=503, content={"detail": "Database temporarily unavailable"})


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
