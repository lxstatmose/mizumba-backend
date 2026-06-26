from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
import importlib.util
import logging
from pathlib import Path
import subprocess
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.audio.router import router as audio_router
from app.auth.router import router as auth_router
from app.channels.router import router as channels_router
from app.chats.router import router as chats_router
from app.core.config import get_settings
from app.core.database import create_db_and_tables, engine
from app.core.redis import get_redis_client
from app.files.router import router as files_router
from app.messages.router import router as messages_router
from app.notifications.router import router as notifications_router
from app.privacy.router import router as privacy_router
from app.search.router import router as search_router
from app.users.router import router as users_router
from app.websocket.broadcaster import start_redis_pubsub_listener, stop_redis_pubsub_listener
from app.websocket.router import router as websocket_router


settings = get_settings()
logger = logging.getLogger("mizumba")
logging.basicConfig(level=logging.INFO)
started_at = datetime.now(UTC)
rate_limit_state: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _add_security_headers(response) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    create_db_and_tables()
    start_redis_pubsub_listener()
    yield
    await stop_redis_pubsub_listener()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_and_rate_limit(request: Request, call_next):
    if request.url.path in {"/health", "/metrics", "/readiness"}:
        response = await call_next(request)
        _add_security_headers(response)
        return response

    client_host = _client_ip(request)
    now = time.time()
    window_start = now - settings.rate_limit_window_seconds
    timestamps = [ts for ts in rate_limit_state.get(client_host, []) if ts >= window_start]
    if len(timestamps) >= settings.rate_limit_requests:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Too many requests"},
            headers={"Retry-After": str(settings.rate_limit_window_seconds)},
        )
        _add_security_headers(response)
        return response
    timestamps.append(now)
    rate_limit_state[client_host] = timestamps

    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info("%s %s -> %s %.2fms", request.method, request.url.path, response.status_code, duration_ms)
    _add_security_headers(response)
    return response

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)
app.include_router(audio_router, prefix=settings.api_v1_prefix)
app.include_router(channels_router, prefix=settings.api_v1_prefix)
app.include_router(chats_router, prefix=settings.api_v1_prefix)
app.include_router(files_router, prefix=settings.api_v1_prefix)
app.include_router(messages_router, prefix=settings.api_v1_prefix)
app.include_router(notifications_router, prefix=settings.api_v1_prefix)
app.include_router(privacy_router, prefix=settings.api_v1_prefix)
app.include_router(search_router, prefix=settings.api_v1_prefix)
app.include_router(websocket_router, prefix=settings.api_v1_prefix)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readiness", tags=["system"])
async def readiness_check() -> dict[str, str | dict[str, str | bool]]:
    checks: dict[str, str | bool] = {}

    try:
        from sqlalchemy import text

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc.__class__.__name__}"

    try:
        await get_redis_client().ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"

    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        checks["ffmpeg"] = "ok"
    except Exception as exc:
        checks["ffmpeg"] = f"error: {exc.__class__.__name__}"

    if settings.enable_whisper_transcription:
        checks["whisper"] = "ok" if importlib.util.find_spec("whisper") is not None else "error: not installed"
    else:
        checks["whisper"] = "disabled"
    status_value = "ok" if all(value in {"ok", True, "disabled"} for value in checks.values()) else "degraded"
    return {"status": status_value, "checks": checks}


@app.get("/metrics", tags=["system"])
def metrics() -> dict[str, str | int | float]:
    uptime_seconds = (datetime.now(UTC) - started_at).total_seconds()
    return {
        "status": "ok",
        "app": settings.app_name,
        "env": settings.app_env,
        "uptime_seconds": round(uptime_seconds, 2),
        "tracked_rate_limit_clients": len(rate_limit_state),
    }
