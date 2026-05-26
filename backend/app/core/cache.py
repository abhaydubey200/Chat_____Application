import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

_cache: redis.Redis | None = None


async def init_cache() -> redis.Redis | None:
    global _cache
    if not settings.REDIS_ENABLED:
        _cache = None
        return None
    if not settings.REDIS_URL:
        raise ValueError("REDIS_URL must be configured when REDIS_ENABLED=true.")
    _cache = redis.from_url(settings.REDIS_URL, decode_responses=True)
    await _cache.ping()
    return _cache


def get_cache() -> redis.Redis | None:
    return _cache


async def close_cache() -> None:
    if _cache:
        await _cache.close()


def conversation_list_key(user_id: str) -> str:
    return f"conversations:list:{user_id}"


def conversation_detail_key(user_id: str, conversation_id: str) -> str:
    return f"conversations:detail:{user_id}:{conversation_id}"


async def cache_json_get(cache: redis.Redis, key: str) -> Any | None:
    payload = await cache.get(key)
    if payload is None:
        return None
    return json.loads(payload)


async def cache_json_set(cache: redis.Redis, key: str, payload: Any, ttl_seconds: int) -> None:
    await cache.set(key, json.dumps(payload), ex=ttl_seconds)


async def invalidate_conversation_cache(
    cache: redis.Redis | None,
    user_id: str,
    conversation_id: str | None = None,
) -> None:
    if not cache:
        return
    keys = [conversation_list_key(user_id)]
    if conversation_id:
        keys.append(conversation_detail_key(user_id, conversation_id))
    await cache.delete(*keys)
