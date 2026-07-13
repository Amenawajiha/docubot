"""
Health endpoints.

GET /health           — lightweight liveness check (no deps)
GET /health/chatbot-engine — checks Qdrant + Celery connectivity
"""

from fastapi import APIRouter
from app.schemas.knowledge import ChatbotEngineHealth

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness check")
async def health() -> dict:
    return {"status": "ok"}


@router.get(
    "/health/chatbot-engine",
    response_model=ChatbotEngineHealth,
    summary="Chatbot engine dependency health",
    description="Checks connectivity to Qdrant and Celery broker.",
)
async def chatbot_engine_health() -> ChatbotEngineHealth:
    qdrant_ok  = await _check_qdrant()
    celery_ok  = _check_celery()

    overall = "ok" if (qdrant_ok and celery_ok) else "degraded"

    return ChatbotEngineHealth(
        status=overall,
        qdrant_connected=qdrant_ok,
        celery_connected=celery_ok,
        version="0.1.0",
    )


async def _check_qdrant() -> bool:
    try:
        from app.infrastructure.vector_db.qdrant_client import get_qdrant_client
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except Exception:
        return False


def _check_celery() -> bool:
    try:
        from app.infrastructure.queue.celery_app import celery_app
        inspect = celery_app.control.inspect(timeout=2)
        stats   = inspect.stats()
        return stats is not None and len(stats) > 0
    except Exception:
        return False