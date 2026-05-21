import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.api.routes import auth, conversations, chat

# Set up structured logging
logging.basicConfig(
    level=logging.INFO if settings.ENV == "production" else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

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

# Configure CORS based on environment
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# GZIP compression for responses
app.add_middleware(GZIPMiddleware, minimum_size=1000)

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

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown."""
    from app.core.database import close_db
    
    logger.info(f"Shutting down {settings.PROJECT_NAME}")
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
