import logging
import time
import uuid
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

# Set up structured logging
logging.basicConfig(
    level=logging.INFO if settings.ENV == "production" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None
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
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every request for tracing."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Basic request logging middleware
@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log request method, path, status, and latency."""
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000
    request_id = getattr(request.state, "request_id", "-")
    logger.info(
        "HTTP %s %s %s %.2fms rid=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        request_id,
    )
    return response

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

# Structured exception handler with request tracing
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    logger.error(
        f"Unhandled error",
        extra={
            "method": request.method,
            "path": request.url.path,
            "error_type": type(exc).__name__,
            "error_msg": str(exc)
        },
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )

# Include Router Modules
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(conversations.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize app on startup."""
    from app.core.database import verify_database_connection, init_db
    
    logger.info(f"Starting {settings.PROJECT_NAME} (env={settings.ENV})")
    
    # Verify database is reachable
    is_healthy = await verify_database_connection()
    if not is_healthy:
        logger.error("Database health check failed. Cannot start application.")
        raise RuntimeError("Database is not accessible.")
    
    # Initialize database schema
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    if settings.REDIS_ENABLED:
        await init_cache()
        logger.info("Redis cache initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    from app.core.database import close_db
    
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
    await close_cache()
    await close_db()

@app.get("/health")
async def health_check():
    """Health check endpoint with full diagnostics."""
    from app.core.database import verify_database_connection
    
    db_healthy = await verify_database_connection()
    
    return {
        "status": "healthy" if db_healthy else "degraded",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENV,
        "database": "ok" if db_healthy else "error"
    }

@app.get("/")
async def root():
    """Welcome route."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} Orchestration API",
        "version": "1.0.0",
        "docs": "/docs" if settings.ENV != "production" else None
    }
