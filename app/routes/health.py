from fastapi import APIRouter
import time
import psutil
from app.redis_client import redis_client
from app.kafka_client import kafka_client
from app.config import config

router = APIRouter()

@router.get("/health")
async def health():
    """Health check endpoint - no auth required"""
    start = time.time()
    
    # Check Redis
    redis_status = "✅ connected" if redis_client.client else "❌ disconnected"
    if redis_client.client:
        try:
            await redis_client.client.ping()
            redis_status = "✅ connected"
        except:
            redis_status = "❌ ping failed"
    
    # Check Kafka
    kafka_status = "✅ connected" if kafka_client.producer else "❌ disconnected"
    
    # System stats
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    return {
        "status": "🚀 ULTRA OPTIMIZED AI API",
        "version": "3.0",
        "timestamp": time.time(),
        "response_time_ms": round((time.time() - start) * 1000, 2),
        "services": {
            "redis": redis_status,
            "kafka": kafka_status,
            "cache_enabled": config.CACHE_ENABLED,
            "streaming_enabled": config.STREAMING_ENABLED
        },
        "system": {
            "cpu_percent": cpu_percent,
            "memory_used_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2)
        },
        "models": {
            "chat": config.CHAT_MODEL,
            "code": config.CODE_MODEL,
            "image": config.IMAGE_MODEL,
            "whisper": config.WHISPER_MODEL
        }
    }
