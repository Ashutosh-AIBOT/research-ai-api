from fastapi import APIRouter, Depends
import time
import logging
from app.config import config
from app.redis_client import redis_client
from app.kafka_client import kafka_client
from app.routes.auth import verify_key

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health():
    """Health check - shows model loading status"""
    # Check Redis
    redis_status = "disconnected"
    if redis_client and redis_client.client:
        try:
            await redis_client.client.ping()
            redis_status = "connected"
        except:
            pass
    
    # Check Kafka
    kafka_status = "disconnected"
    if kafka_client and kafka_client.producer:
        kafka_status = "connected"
    
    return {
        "status": "✅ running",
        "version": "3.0",
        "mode": "on-demand loading",
        "services": {
            "redis": redis_status,
            "kafka": kafka_status
        },
        "models": {
            "whisper": "not loaded (loads on first /stt)",
            "translator": "not loaded (loads on first /translate)",
            "chat": f"{config.CHAT_MODEL} (loads on first /chat)",
            "code": f"{config.CODE_MODEL} (loads on first /code)",
            "image": f"{config.IMAGE_MODEL} (loads on first /image)"
        },
        "cache_enabled": config.CACHE_ENABLED,
        "streaming_enabled": config.STREAMING_ENABLED,
        "timestamp": time.time()
    }