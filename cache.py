"""
Redis-based caching layer for high-performance data access.
Reduces database load for 100K+ concurrent users.
"""

import json
import logging
from typing import Optional, Any
from functools import wraps

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from config import config

logger = logging.getLogger(__name__)


class CacheManager:
    """Redis cache manager with connection pooling."""

    def __init__(self):
        """Initialize cache manager."""
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[redis.Redis] = None

    async def initialize(self) -> None:
        """Initialize Redis connection pool."""
        try:
            self.pool = ConnectionPool.from_url(
                config.REDIS_URL,
                max_connections=config.REDIS_POOL_SIZE,
                decode_responses=True,
            )
            self.redis = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            await self.redis.ping()
            
            logger.info("✅ Redis cache initialized")

        except Exception as e:
            logger.exception(f"Failed to initialize Redis cache: {e}")
            # Don't raise - bot can work without cache (degraded performance)
            self.redis = None

    async def close(self) -> None:
        """Close Redis connections."""
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()
        logger.info("Redis cache closed")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = config.CACHE_TTL
    ) -> bool:
        """Set value in cache with TTL."""
        if not self.redis:
            return False

        try:
            serialized = json.dumps(value)
            await self.redis.setex(key, ttl, serialized)
            return True

        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True

        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter in cache."""
        if not self.redis:
            return None

        try:
            return await self.redis.incrby(key, amount)

        except Exception as e:
            logger.warning(f"Cache increment error for key {key}: {e}")
            return None

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        if not self.redis:
            return False

        try:
            await self.redis.expire(key, ttl)
            return True

        except Exception as e:
            logger.warning(f"Cache expire error for key {key}: {e}")
            return False

    # ============ Cache Key Helpers ============

    @staticmethod
    def user_balance_key(user_id: int) -> str:
        """Generate cache key for user balance."""
        return f"user:{user_id}:balance"

    @staticmethod
    def user_model_key(user_id: int) -> str:
        """Generate cache key for user model."""
        return f"user:{user_id}:model"

    @staticmethod
    def user_rate_limit_key(user_id: int, window: str) -> str:
        """Generate cache key for rate limiting."""
        return f"ratelimit:{user_id}:{window}"

    @staticmethod
    def global_rate_limit_key() -> str:
        """Generate cache key for global rate limiting."""
        return "ratelimit:global"


# Global cache instance
cache = CacheManager()


def cached(ttl: int = config.CACHE_TTL, key_prefix: str = ""):
    """
    Decorator for caching function results.
    
    Note: Uses SHA1 hash of arguments for deterministic, fixed-length keys.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import hashlib
            import json
            
            # Generate deterministic cache key using hash
            try:
                raw_key = json.dumps(
                    {"args": str(args), "kwargs": str(kwargs)}, 
                    sort_keys=True
                )
                hashed = hashlib.sha1(raw_key.encode()).hexdigest()
                cache_key = f"{key_prefix}:{func.__name__}:{hashed}"
            except Exception:
                # Fallback to simple key if serialization fails
                cache_key = f"{key_prefix}:{func.__name__}:fallback"
            
            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Store in cache
            await cache.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator
