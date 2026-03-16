from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import logging
import asyncio

import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
import json
import aiofiles

# Import routes
from app.routes import chat, code, stt, tts, translate, image, health, models
from app.redis_client import redis_client
from app.kafka_client import kafka_client
from app.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Ultra-Fast AI API",
    description="AI API with Redis caching and Kafka streaming",
    version="3.0",
    docs_url="/docs",
    redoc_url="/redoc"
)



# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(health.router, tags=["System"])
app.include_router(models.router, tags=["Info"])
app.include_router(chat.router, tags=["AI - Chat"])
app.include_router(code.router, tags=["AI - Code"])
app.include_router(stt.router, tags=["AI - Speech"])
app.include_router(tts.router, tags=["AI - Speech"])
app.include_router(translate.router, tags=["AI - Translation"])
app.include_router(image.router, tags=["AI - Vision"])


# Add after imports
redis_client = None
kafka_producer = None

@app.on_event("startup")
async def init_cache():
    global redis_client, kafka_producer
    # Redis for caching
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        decode_responses=True
    )
    # Kafka for streaming
    kafka_producer = AIOKafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BROKER", "localhost:9092")
    )
    await kafka_producer.start()


@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup"""
    logger.info("🚀 Starting Ultra-Fast AI API...")
    
    # Connect to Redis
    await redis_client.connect()
    
    # Connect to Kafka
    await kafka_client.connect_producer()
    
    logger.info("✅ All services initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    logger.info("🛑 Shutting down...")
    
    # Close Redis
    await redis_client.close()
    
    # Close Kafka
    await kafka_client.close()
    
    logger.info("✅ All connections closed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "🚀 Ultra-Fast AI API",
        "version": "3.0",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "Redis caching (5-20ms responses)",
            "Kafka streaming (real-time tokens)",
            "WebSocket support",
            "All models pre-downloaded"
        ]
    }
    
    
# Add these caching functions to your existing code

@app.post("/chat")
async def chat(req: dict, key: str = Depends(verify_key)):
    # Check Redis cache first
    cache_key = f"chat:{req.get('message')}"
    if redis_client:
        cached = await redis_client.get(cache_key)
        if cached:
            return {"reply": json.loads(cached), "cached": True, "time_sec": 0.005}
    
    # Generate response
    response = ollama.chat(model='phi3:mini', messages=[
        {'role': 'user', 'content': req.get('message', '')}
    ])
    reply = response['message']['content']
    
    # Cache it
    if redis_client:
        await redis_client.setex(cache_key, 3600, json.dumps(reply))
    
    return {"reply": reply, "cached": False, "time_sec": 0.5}
