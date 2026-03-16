import json
import hashlib
import logging
from app.config import config
from app.redis_client import redis_client

logger = logging.getLogger(__name__)

class CacheHelper:
    def __init__(self):
        self.enabled = config.CACHE_ENABLED
    
    def generate_key(self, *args):
        """Generate cache key from arguments"""
        key_str = ":".join(str(arg) for arg in args)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, prefix: str, *args):
        """Get from cache"""
        if not self.enabled or not redis_client or not redis_client.client:
            return None
        
        key = f"{prefix}:{self.generate_key(*args)}"
        try:
            data = await redis_client.client.get(key)
            if data:
                logger.debug(f"Cache hit: {key}")
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
        return None
    
    async def set(self, prefix: str, value, *args, ttl: int = None):
        """Set in cache"""
        if not self.enabled or not redis_client or not redis_client.client:
            return
        
        key = f"{prefix}:{self.generate_key(*args)}"
        ttl = ttl or config.REDIS_TTL
        try:
            await redis_client.client.setex(key, ttl, json.dumps(value))
            logger.debug(f"Cached: {key} for {ttl}s")
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
    
    async def get_or_compute(self, prefix: str, compute_func, *args, ttl: int = None):
        """Get from cache or compute and cache"""
        # Try cache first
        cached = await self.get(prefix, *args)
        if cached:
            return cached
        
        # Compute and cache
        result = await compute_func()
        await self.set(prefix, result, *args, ttl=ttl)
        return result

cache_helper = CacheHelper()