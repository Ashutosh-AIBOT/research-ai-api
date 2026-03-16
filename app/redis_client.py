import json
import redis.asyncio as redis
from app.config import config
import logging

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.client = None
        self.enabled = config.CACHE_ENABLED
        
    async def connect(self):
        """Connect to Redis"""
        if not self.enabled:
            logger.info("Redis caching is disabled")
            return
            
        try:
            self.client = await redis.from_url(
                f"redis://{config.REDIS_HOST}:{config.REDIS_PORT}/{config.REDIS_DB}",
                password=config.REDIS_PASSWORD,
                decode_responses=True
            )
            await self.client.ping()
            logger.info("✅ Connected to Redis")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.enabled = False
    
    async def get(self, key: str):
        """Get value from cache"""
        if not self.enabled or not self.client:
            return None
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = None):
        """Set value in cache with TTL"""
        if not self.enabled or not self.client:
            return False
        try:
            ttl = ttl or config.REDIS_TTL
            return await self.client.setex(key, ttl, value)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def set_json(self, key: str, value: dict, ttl: int = None):
        """Set JSON value in cache"""
        return await self.set(key, json.dumps(value), ttl)
    
    async def get_json(self, key: str):
        """Get JSON value from cache"""
        data = await self.get(key)
        return json.loads(data) if data else None
    
    async def delete(self, key: str):
        """Delete from cache"""
        if not self.enabled or not self.client:
            return False
        try:
            return await self.client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def clear_pattern(self, pattern: str):
        """Clear keys matching pattern"""
        if not self.enabled or not self.client:
            return 0
        try:
            keys = await self.client.keys(pattern)
            if keys:
                return await self.client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear pattern error: {e}")
            return 0
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")

# Global Redis instance
redis_client = RedisClient()
