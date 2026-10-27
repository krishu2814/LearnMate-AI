import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import logger, setup_logging
from app.db.redis import check_redis_health, close_redis
from app.db.session import check_db_health, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle management: startup and graceful shutdown."""
    setup_logging()
    logger.info("app_starting", app_name=settings.PROJECT_NAME, env=settings.ENVIRONMENT)

    yield

    logger.info("app_shutting_down")
    await close_redis()
    await engine.dispose()
    logger.info("app_stopped_cleanly")


def create_application() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description="Production-grade AI-Powered Personalized Learning Platform Backend",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict to specific frontend domains in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time"],
    )

    # Request ID and Latency Middleware
    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        response: Response = await call_next(request)

        process_time = time.perf_counter() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        return response

    # -------------------------------------------------------------
    # Health Endpoints
    # -------------------------------------------------------------
    @app.get("/health/live", tags=["Health"], summary="Liveness Probe")
    async def liveness_check() -> dict:
        """Kubernetes/Docker liveness check. Always returns 200 when container is running."""
        return {
            "status": "ok",
            "app": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/health/ready", tags=["Health"], summary="Readiness Probe")
    async def readiness_check() -> JSONResponse:
        """Kubernetes/Docker readiness check. Validates DB & Redis connectivity."""
        db_healthy = await check_db_health()
        redis_healthy = await check_redis_health()

        is_ready = db_healthy and redis_healthy
        http_status = status.HTTP_200_OK if is_ready else status.HTTP_503_SERVICE_UNAVAILABLE

        payload = {
            "status": "ready" if is_ready else "degraded",
            "checks": {
                "database": "connected" if db_healthy else "disconnected",
                "redis": "connected" if redis_healthy else "disconnected",
            },
        }
        return JSONResponse(status_code=http_status, content=payload)

    @app.get("/", tags=["Root"])
    async def root() -> dict:
        return {
            "message": f"Welcome to {settings.PROJECT_NAME} API",
            "documentation": "/docs",
            "health": "/health/live",
        }

    return app


app = create_application()
