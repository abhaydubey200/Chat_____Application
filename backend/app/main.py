import logging
import time
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from app.core.config import settings
from app.core.limiter import limiter
from app.core.cache import init_cache, close_cache
from app.api.routes import auth, conversations, chat
from app.core.observability import (
    configure_structured_logging,
    get_logger,
    RequestContext,
    set_request_context,
    get_request_context,
    clear_context,
    get_metrics,
)

# Configure structured JSON logging
log_level = logging.DEBUG if settings.ENV == "development" else logging.INFO
configure_structured_logging(level=log_level, use_json=True)
logger = get_logger(__name__)

# Application lifespan handler (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown with comprehensive diagnostics."""
    from app.core.database import verify_database_connection, init_db, close_db

    # --- STARTUP ---
    logger.info(
        f"Starting {settings.PROJECT_NAME}",
        extra={
            'event_type': 'startup_start',
            'environment': settings.ENV,
            'version': '1.0.0',
        }
    )

    logger.info(
        "Configuration loaded",
        extra={
            'event_type': 'configuration_validated',
            'environment': settings.ENV,
            'llm_provider': settings.LLM_PROVIDER,
            'database_configured': bool(settings.DATABASE_URL),
            'redis_enabled': settings.REDIS_ENABLED,
        }
    )

    # Verify database
    try:
        is_healthy = await verify_database_connection()
        if not is_healthy:
            logger.error(
                "Database health check failed",
                extra={'event_type': 'startup_failure', 'reason': 'database_unavailable'}
            )
            raise RuntimeError("Database is not accessible.")
        logger.info("Database connection verified", extra={'event_type': 'database_healthy'})
    except Exception as e:
        logger.error(
            "Failed to verify database connection",
            extra={'event_type': 'startup_failure', 'reason': 'database_error', 'error_type': type(e).__name__},
            exc_info=True
        )
        raise

    # Initialize schema
    try:
        await init_db()
        logger.info("Database schema initialized", extra={'event_type': 'database_initialized'})
    except Exception as e:
        logger.error(
            "Failed to initialize database schema",
            extra={'event_type': 'startup_failure', 'reason': 'schema_initialization_failed', 'error_type': type(e).__name__},
            exc_info=True
        )
        raise

    if settings.REDIS_ENABLED:
        try:
            await init_cache()
            logger.info("Redis cache initialized", extra={'event_type': 'cache_initialized'})
        except Exception as e:
            logger.warning(
                "Failed to initialize Redis cache",
                extra={'event_type': 'cache_init_failed', 'error_type': type(e).__name__, 'fallback': 'using_in_memory_cache'}
            )

    logger.info(
        f"{settings.PROJECT_NAME} started successfully",
        extra={'event_type': 'startup_complete'}
    )

    yield  # Application runs here

    # --- SHUTDOWN ---
    logger.info(f"Shutting down {settings.PROJECT_NAME}", extra={'event_type': 'shutdown_start'})

    try:
        await close_cache()
        logger.info("Cache closed", extra={'event_type': 'cache_closed'})
    except Exception as e:
        logger.warning("Error closing cache", extra={'error_type': type(e).__name__})

    try:
        await close_db()
        logger.info("Database closed", extra={'event_type': 'database_closed'})
    except Exception as e:
        logger.warning("Error closing database", extra={'error_type': type(e).__name__})

    metrics = get_metrics()
    snapshot = metrics.get_snapshot()
    logger.info(
        "Final metrics snapshot",
        extra={'event_type': 'shutdown_complete', 'metrics': snapshot.to_dict()}
    )

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
    lifespan=lifespan,
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda req, exc: JSONResponse(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    content={"detail": "Rate limit exceeded. Please try again later."}
))
app.add_middleware(SlowAPIMiddleware)

# Configure CORS based on environment
allowed_origin_regex = None
if settings.ENV == "production":
    if not settings.CORS_ORIGINS:
        logger.error("CORS_ORIGINS not configured for production mode. API requests will fail.")
        raise ValueError("CORS_ORIGINS must be configured in production.")
    allowed_origins = settings.CORS_ORIGINS
else:
    # Development: allow localhost and common dev URLs
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    if settings.CORS_ORIGINS:
        allowed_origins.extend(settings.CORS_ORIGINS)
    allowed_origin_regex = r"^http://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+):3000$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZIP compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Request ID tracing middleware
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Initialize request context with tracing IDs and metadata."""
    # Create request context
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    client_host = request.client.host if request.client else "unknown"
    
    # Extract user_id from JWT if available (will be set in route)
    user_id = None
    
    # Create and set context
    ctx = RequestContext(
        request_id=request_id,
        user_id=user_id,
        http_method=request.method,
        http_path=request.url.path,
        client_ip=client_host,
        user_agent=request.headers.get("user-agent", ""),
        start_time=datetime.utcnow(),
    )
    set_request_context(ctx)
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        
        # Update context with response info
        ctx.http_status = response.status_code
        ctx.end_time = datetime.utcnow()
        
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        # Log request completion
        if ctx.end_time:
            logger.log_request_end(
                method=ctx.http_method,
                path=ctx.http_path,
                status_code=ctx.http_status or 500,
                duration_ms=ctx.duration_ms() or 0,
                client_ip=ctx.client_ip,
            )
        clear_context()

# Request size limit middleware
MAX_BODY_SIZE = 2 * 1024 * 1024  # 2MB max request size

@app.middleware("http")
async def size_limit_middleware(request: Request, call_next):
    """Enforce maximum request body size."""
    if request.method in ["POST", "PATCH"]:
        if request.headers.get("content-length"):
            try:
                content_length = int(request.headers.get("content-length"))
                if content_length > MAX_BODY_SIZE:
                    return JSONResponse(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        content={"detail": f"Request body size exceeds maximum allowed ({MAX_BODY_SIZE} bytes)."}
                    )
            except ValueError:
                pass
    return await call_next(request)

# Global exception handler with structured error logging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler with observability context."""
    from app.core.observability.error_types import get_error_category
    
    request_ctx = get_request_context()
    error_category = get_error_category(exc)
    
    logger.error(
        f"Unhandled exception: {type(exc).__name__}",
        extra={
            'event_type': 'unhandled_error',
            'method': request.method,
            'path': request.url.path,
            'error_type': type(exc).__name__,
            'error_message': str(exc),
            'error_category': error_category.value,
        },
        exc_info=True
    )
    
    # Update metrics
    get_metrics().increment_failed_requests()
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# Include Router Modules
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(conversations.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    """Health check endpoint with full diagnostics."""
    from app.core.database import verify_database_connection
    
    db_healthy = await verify_database_connection()
    metrics_snapshot = get_metrics().get_snapshot()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENV,
        "database": "ok" if db_healthy else "error",
        "metrics": {
            "active_streams": metrics_snapshot.active_streams,
            "total_requests": metrics_snapshot.total_requests,
            "failed_requests": metrics_snapshot.failed_requests,
            "provider_rate_limits_hit": metrics_snapshot.provider_rate_limits_hit,
            "provider_timeouts": metrics_snapshot.provider_timeouts,
        }
    }

@app.get("/metrics")
async def get_metrics_endpoint():
    """Get current metrics snapshot."""
    metrics_snapshot = get_metrics().get_snapshot()
    return metrics_snapshot.to_dict()

@app.get("/")
async def root():
    """Welcome route."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} Orchestration API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENV != "production" else None
    }
