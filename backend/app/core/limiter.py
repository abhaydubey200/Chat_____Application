from slowapi import Limiter
from slowapi.util import get_remote_address
from app.core.config import settings

storage_uri = settings.RATE_LIMIT_STORAGE_URL
if not storage_uri and settings.REDIS_ENABLED and settings.REDIS_URL:
    storage_uri = settings.REDIS_URL

# Shared limiter instance used by both main.py and individual route modules
limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri)
