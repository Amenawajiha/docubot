from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import auth as auth_router
from app.api import workspaces as workspaces_router
from app.api import chatbots as chatbots_router
from app.api import knowledge as knowledge_router
from app.api import internal as internal_router
from app.api import health as health_router
from app.api import chat as chat_router
from app.api import analytics as analytics_router
from app.api import deployment as deployment_router
from app.api import billing as billing_router
from app.api import playground as playground_router
from app.api import dashboard as dashboard_router
from app.config import settings
from app.data import database
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.utils.exceptions import AppException

import asyncio

async def _purge_task():
    from app.core.chatbot.service import purge_expired_chatbots
    from app.data.database import async_session_maker
    import logging
    while True:
        try:
            # Run once a day
            await asyncio.sleep(60) # Run every minute for testing
            async with async_session_maker() as session:
                deleted = await purge_expired_chatbots(session)
                if deleted > 0:
                    logging.info(f"Purged {deleted} expired chatbots.")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Error purging expired chatbots: {e}")
            await asyncio.sleep(3600) # Retry later if error

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup: engine is created lazily on first request — nothing to do here.
    try:
        from app.infrastructure.storage.s3_client import ensure_bucket_exists
        await ensure_bucket_exists()
    except Exception as e:
        import logging
        logging.error(f"Failed to ensure S3 bucket exists: {e}")
        
    purge_task_handle = asyncio.create_task(_purge_task())
        
    yield
    # Shutdown: dispose the connection pool only if it was ever initialised.
    purge_task_handle.cancel()
    
    engine = database.get_engine_or_none()
    if engine is not None:
        await engine.dispose()
    from app.infrastructure.vector_db.qdrant_client import close_qdrant_client
    await close_qdrant_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title="DocuBot API",
        version="0.1.0",
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url="/api/redoc" if not settings.is_production else None,
        openapi_url="/api/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # app.add_middleware(RateLimitMiddleware)

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    app.include_router(auth_router.router, prefix="/api/v1")
    app.include_router(workspaces_router.router, prefix="/api/v1")
    app.include_router(chatbots_router.router, prefix="/api/v1")
    app.include_router(knowledge_router.router, prefix="/api/v1")
    app.include_router(internal_router.router, prefix="/api")
    app.include_router(health_router.router)
    app.include_router(chat_router.router, prefix="/api/v1")
    app.include_router(analytics_router.router, prefix="/api/v1")
    app.include_router(billing_router.router, prefix="/api/v1")
    app.include_router(deployment_router.router, prefix="/api/v1")
    app.include_router(playground_router.router, prefix="/api/v1")
    app.include_router(dashboard_router.router, prefix="/api/v1")

    return app


app = create_app()