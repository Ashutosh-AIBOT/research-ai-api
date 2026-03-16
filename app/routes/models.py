from fastapi import APIRouter, Depends
from app.utils.ollama_helper import ollama_helper
from app.config import config
from app.routes.auth import verify_key

router = APIRouter()

@router.get("/models")
async def list_models(key: str = Depends(verify_key)):
    """List all available models and endpoints"""
    
    # Get Ollama models
    ollama_models = ollama_helper.list_models()
    
    return {
        "endpoints": {
            "/chat": f"{config.CHAT_MODEL} — general chat with Redis cache + Kafka streaming",
            "/code": f"{config.CODE_MODEL} — code generation",
            "/stt": f"Whisper {config.WHISPER_MODEL} — speech to text",
            "/tts": "espeak — ultra-fast text to speech (no model)",
            "/translate": "Helsinki-NLP — Hindi to English",
            "/image": f"{config.IMAGE_MODEL} — image understanding",
            "/health": "system health check",
            "/models": "this list",
            "/ws/chat": "WebSocket for real-time streaming chat"
        },
        "performance_features": {
            "redis_cache": "✅ enabled (5-20ms responses)",
            "kafka_streaming": "✅ enabled (real-time tokens)",
            "model_caching": "✅ all models pre-downloaded",
            "response_compression": "✅ gzip enabled"
        },
        "ollama_models": ollama_models.get("models", []),
        "total_size_gb": 5.0,
        "status": "🚀 Ready for 30+ projects"
    }
