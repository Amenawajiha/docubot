"""
Health endpoints.

GET /health           — lightweight liveness check (no deps)
GET /health/readiness — readiness check for DB, Qdrant, Redis, MinIO
GET /health/chatbot-engine — checks Qdrant + Celery connectivity
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.schemas.health import HealthReadinessOut, ServiceStatuses
from app.schemas.knowledge import ChatbotEngineHealth

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
async def health() -> dict:
    return {"status": "ok"}


@router.get(
    "/health/readiness",
    response_model=HealthReadinessOut,
    summary="Readiness check",
    description="Checks connectivity for core (PostgreSQL, Qdrant) and optional (Redis, MinIO) services.",
)
async def readiness() -> JSONResponse:
    db_ok = await _check_db()
    qdrant_ok = await _check_qdrant()
    redis_ok = await _check_redis()
    minio_ok = await _check_minio()

    services = ServiceStatuses(
        database="up" if db_ok else "down",
        redis="up" if redis_ok else "down",
        qdrant="up" if qdrant_ok else "down",
        minio="up" if minio_ok else "down",
    )

    core_ok = db_ok and qdrant_ok
    all_ok = core_ok and redis_ok and minio_ok

    if not core_ok:
        status = "unhealthy"
        status_code = 503
    elif not all_ok:
        status = "degraded"
        status_code = 200
    else:
        status = "ok"
        status_code = 200

    payload = HealthReadinessOut(status=status, services=services)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


@router.get(
    "/health/chatbot-engine",
    response_model=ChatbotEngineHealth,
    summary="Chatbot engine dependency health",
    description="Checks connectivity to Qdrant and Celery broker.",
)
async def chatbot_engine_health() -> ChatbotEngineHealth:
    qdrant_ok = await _check_qdrant()
    celery_ok = _check_celery()

    overall = "ok" if (qdrant_ok and celery_ok) else "degraded"

    return ChatbotEngineHealth(
        status=overall,
        qdrant_connected=qdrant_ok,
        celery_connected=celery_ok,
        version="0.1.0",
    )


async def _check_db() -> bool:
    try:
        from app.data.database import _get_engine
        engine = _get_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _check_redis() -> bool:
    try:
        from app.infrastructure.cache.redis_client import get_redis
        client = await get_redis()
        await client.ping()  # type: ignore
        return True
    except Exception:
        return False


async def _check_qdrant() -> bool:
    try:
        from app.infrastructure.vector_db.qdrant_client import get_qdrant_client
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except Exception:
        return False


async def _check_minio() -> bool:
    try:
        from app.infrastructure.storage.s3_client import _get_session
        from app.config import settings
        endpoint = settings.s3_endpoint_url or None
        async with _get_session().client("s3", endpoint_url=endpoint) as s3:
            await s3.list_buckets()
        return True
    except Exception:
        return False


def _check_celery() -> bool:
    try:
        from app.infrastructure.queue.celery_app import celery_app
        inspect = celery_app.control.inspect(timeout=2)
        stats = inspect.stats()
        return stats is not None and len(stats) > 0
    except Exception:
        return False