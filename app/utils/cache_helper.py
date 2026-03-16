import hashlib
import json
from app.redis_client import redis_client
from app.config import config
import logging

logger = logging.getLogger(__name__)

class CacheHelper:
    @staticmethod
    def generate_key(prefix: str, *args, **kwargs):
        """Generate cache key from arguments"""
        key_parts = [prefix]
        
        # Add positional args
        for arg in args:
            if arg:
                key_parts.append(str(arg))
        
        # Add keyword args sorted for consistency
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            for k, v in sorted_kwargs:
                if v is not None:
                    key_parts.append(f"{k}:{v}")
        
        # Join and hash if too long
        key = ":".join(key_parts)
        if len(key) > 200:
            key = f"{prefix}:{hashlib.md5(key.encode()).hexdigest()}"
        
        return key
    
    @staticmethod
    async def get_or_compute(key_prefix, compute_func, ttl=None, *args, **kwargs):
        """Get from cache or compute and cache"""
        if not config.CACHE_ENABLED:
            return await compute_func(*args, **kwargs)
        
        # Generate cache key
        cache_key = CacheHelper.generate_key(key_prefix, *args, **kwargs)
        
        # Try to get from cache
        cached = await redis_client.get_json(cache_key)
        if cached:
            logger.debug(f"Cache hit: {cache_key}")
            return cached
        
        # Compute and cache
        logger.debug(f"Cache miss: {cache_key}")
        result = await compute_func(*args, **kwargs)
        
        # Cache if result is not too large (avoid caching huge responses)
        if isinstance(result, dict) and len(json.dumps(result)) < 100000:
            await redis_client.set_json(cache_key, result, ttl)
        
        return result
    
    @staticmethod
    async def invalidate_pattern(pattern: str):
        """Invalidate cache by pattern"""
        return await redis_client.clear_pattern(pattern)

cache_helper = CacheHelper()
