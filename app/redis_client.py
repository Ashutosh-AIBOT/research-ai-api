import redis.asyncio as redis
import json
import logging
from app.config import config

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.client = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = await redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                db=config.REDIS_DB,
                password=config.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2
            )
            await self.client.ping()
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
            self.client = None
    
    async def close(self):
        if self.client:
            await self.client.close()
    
    async def set_json(self, key: str, value, ttl: int = None):
        if not self.client:
            return
        ttl = ttl or config.REDIS_TTL
        await self.client.setex(key, ttl, json.dumps(value))
    
    async def get_json(self, key: str):
        if not self.client:
            return None
        data = await self.client.get(key)
        return json.loads(data) if data else None

redis_client = RedisClient()