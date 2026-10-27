from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

_redis_pool: Optional[aioredis.ConnectionPool] = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


def get_redis_client() -> aioredis.Redis:
    pool = get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


async def check_redis_health() -> bool:
    """Send PING to Redis server to verify connectivity."""
    try:
        client = get_redis_client()
        pong = await client.ping()
        return pong is True or pong == "PONG"
    except Exception:
        return False


async def close_redis() -> None:
    """Gracefully close Redis connection pool during app shutdown."""
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
