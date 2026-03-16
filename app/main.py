# Add at the very top of main.py
import setuptools
import pkg_resources
import os
import time
import json
import logging
import asyncio
from functools import lru_cache
from typing import Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import APIKeyHeader
import redis.asyncio as redis
from aiokafka import AIOKafkaProducer
import aiofiles
import httpx
import torch

# Import from app modules
from app.redis_client import redis_client
from app.kafka_client import kafka_client
from app.config import config
from app.utils.ollama_helper import ollama_helper

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== API KEY SECURITY ==========
API_KEY = os.getenv("API_KEY", "mypassword123")
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_key(key: str = Depends(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="❌ Wrong API Key")
    return key

# ========== ON-DEMAND MODEL LOADING (Load only when needed!) ==========

@lru_cache(maxsize=1)
def get_whisper_model():
    """Load Whisper model only when first /stt endpoint is called"""
    logger.info("📥 Loading Whisper model (first time only)...")
    import whisper
    start = time.time()
    model = whisper.load_model('tiny', download_root='/app/models/whisper')
    logger.info(f"✅ Whisper model loaded in {time.time()-start:.2f}s")
    return model

@lru_cache(maxsize=1)
def get_translator_model():
    """Load Translator model only when first /translate endpoint is called"""
    logger.info("📥 Loading Translator model (first time only)...")
    from transformers import MarianMTModel, MarianTokenizer
    start = time.time()
    tokenizer = MarianTokenizer.from_pretrained(
        'Helsinki-NLP/opus-mt-hi-en', 
        cache_dir='/app/models/translator'
    )
    model = MarianMTModel.from_pretrained(
        'Helsinki-NLP/opus-mt-hi-en', 
        cache_dir='/app/models/translator'
    )
    logger.info(f"✅ Translator model loaded in {time.time()-start:.2f}s")
    return tokenizer, model

@lru_cache(maxsize=1)
def get_sentiment_model():
    """Load sentiment model only when needed (optional)"""
    logger.info("📥 Loading Sentiment model (first time only)...")
    from transformers import pipeline
    start = time.time()
    model = pipeline(
        'sentiment-analysis', 
        model='distilbert-base-uncased-finetuned-sst-2-english',
        cache_dir='/app/models/transformers'
    )
    logger.info(f"✅ Sentiment model loaded in {time.time()-start:.2f}s")
    return model

# ========== CREATE FASTAPI APP ==========
app = FastAPI(
    title="Ultra-Fast AI API",
    description="AI API with Redis caching, Kafka streaming, and on-demand model loading",
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

# ========== REDIS & KAFKA CLIENTS ==========
redis_client_instance = None
kafka_producer_instance = None

@app.on_event("startup")
async def startup_event():
    """Initialize connections on startup (NO models loaded yet!)"""
    global redis_client_instance, kafka_producer_instance
    
    logger.info("🚀 Starting Ultra-Fast AI API with ON-DEMAND model loading...")
    
    # Connect to Redis
    try:
        redis_client_instance = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True,
            socket_connect_timeout=2
        )
        await redis_client_instance.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.warning(f"⚠️ Redis not available: {e}")
        redis_client_instance = None
    
    # Connect to Kafka - Use service name 'kafka' NOT localhost!
    try:
        kafka_broker = os.getenv("KAFKA_BROKER", "kafka:9092")  # Critical fix!
        logger.info(f"🔄 Connecting to Kafka at {kafka_broker}")
        kafka_producer_instance = AIOKafkaProducer(
            bootstrap_servers=kafka_broker,
            request_timeout_ms=10000,
            max_request_size=1048576
        )
        await kafka_producer_instance.start()
        logger.info("✅ Kafka connected")
    except Exception as e:
        logger.warning(f"⚠️ Kafka not available: {e}")
        kafka_producer_instance = None
    
    logger.info("✅ Services initialized. Models will load on first use!")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up connections on shutdown"""
    logger.info("🛑 Shutting down...")
    
    if redis_client_instance:
        await redis_client_instance.close()
    
    if kafka_producer_instance:
        await kafka_producer_instance.stop()
    
    # Close ollama helper
    await ollama_helper.close()
    
    logger.info("✅ All connections closed")

# ========== ROOT ENDPOINT ==========
@app.get("/")
async def root():
    """Root endpoint"""
    # Check Kafka status
    kafka_status = "✅ Connected" if kafka_producer_instance else "❌ Not connected"
    
    return {
        "message": "🚀 Ultra-Fast AI API",
        "version": "3.0",
        "docs": "/docs",
        "health": "/health",
        "features": [
            "On-demand model loading (models load only when used)",
            "Redis caching (5-20ms responses for repeated queries)",
            "Kafka streaming (real-time token streaming)",
            "WebSocket support"
        ],
        "redis": "✅ Connected" if redis_client_instance else "❌ Not connected",
        "kafka": kafka_status
    }

# ========== HEALTH CHECK ==========
@app.get("/health")
async def health():
    """Health check - NO models loaded"""
    return {
        "status": "✅ running",
        "mode": "on-demand loading",
        "redis": "connected" if redis_client_instance else "disconnected",
        "kafka": "connected" if kafka_producer_instance else "disconnected",
        "models": {
            "whisper": "not loaded (loads on first /stt)",
            "translator": "not loaded (loads on first /translate)",
            "sentiment": "not loaded (optional)",
            "ollama": "available on demand"
        }
    }

# ========== CHAT ENDPOINT ==========
@app.post("/chat")
async def chat(req: dict, key: str = Depends(verify_key)):
    """Chat endpoint - uses Ollama (loads on first request)"""
    start_time = time.time()
    
    # Check Redis cache first
    cache_key = f"chat:{req.get('message', '')}"
    if redis_client_instance:
        try:
            cached = await redis_client_instance.get(cache_key)
            if cached:
                return {
                    "reply": json.loads(cached),
                    "cached": True,
                    "time_sec": round(time.time() - start_time, 3)
                }
        except Exception as e:
            logger.warning(f"Cache read error: {e}")
    
    # Generate response using ollama_helper
    try:
        prompt = f"User: {req.get('message', '')}\nAssistant:"
        reply = await ollama_helper.generate("phi3:mini", prompt)
        
        # Cache it
        if redis_client_instance:
            await redis_client_instance.setex(cache_key, 3600, json.dumps(reply))
        
        return {
            "reply": reply,
            "model": "phi3:mini",
            "cached": False,
            "time_sec": round(time.time() - start_time, 3)
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")

# ========== CODE ENDPOINT ==========
@app.post("/code")
async def code(req: dict, key: str = Depends(verify_key)):
    """Code endpoint - uses deepseek-coder"""
    start_time = time.time()
    
    try:
        prompt = f"Write code: {req.get('message', '')}\nOnly output code:"
        reply = await ollama_helper.generate("deepseek-coder:1.3b", prompt)
        
        return {
            "code": reply,
            "model": "deepseek-coder:1.3b",
            "time_sec": round(time.time() - start_time, 3)
        }
    except Exception as e:
        logger.error(f"Code error: {e}")
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")

# ========== STT ENDPOINT (Loads Whisper on first call) ==========
@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...), key: str = Depends(verify_key)):
    """Speech to text - loads Whisper model ONLY on first request"""
    start_time = time.time()
    
    # Load model on demand (only first time)
    whisper_model = get_whisper_model()
    
    # Save uploaded file temporarily
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    content = await file.read()
    tmp.write(content)
    tmp.close()
    
    try:
        logger.info(f"🎤 Transcribing audio ({len(content)} bytes)...")
        result = whisper_model.transcribe(tmp.name, fp16=False)
        return {
            "text": result["text"],
            "language": result["language"],
            "time_sec": round(time.time() - start_time, 3)
        }
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp.name)

# ========== TRANSLATE ENDPOINT (Loads Translator on first call) ==========
@app.post("/translate")
async def translate(req: dict, key: str = Depends(verify_key)):
    """Hindi to English translation - loads model ONLY on first request"""
    start_time = time.time()
    
    # Load model on demand
    tokenizer, model = get_translator_model()
    
    text = req.get('text', '')
    logger.info(f"🔄 Translating: {text[:50]}...")
    
    try:
        tokens = tokenizer([text], return_tensors="pt", padding=True)
        translated = model.generate(**tokens, max_length=128)
        result = tokenizer.decode(translated[0], skip_special_tokens=True)
        
        return {
            "original": text,
            "translated": result,
            "time_sec": round(time.time() - start_time, 3)
        }
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ========== IMAGE ENDPOINT ==========
@app.post("/image")
async def image_understand(
    file: UploadFile = File(...),
    question: str = "What is in this image?",
    key: str = Depends(verify_key)
):
    """Image understanding - uses moondream via Ollama"""
    start_time = time.time()
    
    import tempfile
    import base64
    
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    content = await file.read()
    tmp.write(content)
    tmp.close()
    
    try:
        logger.info(f"🖼️ Analyzing image ({len(content)} bytes)...")
        
        with open(tmp.name, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        response = await ollama_helper.generate_with_image(
            "moondream", 
            question, 
            img_b64
        )
        
        return {
            "answer": response,
            "time_sec": round(time.time() - start_time, 3)
        }
    except Exception as e:
        logger.error(f"Image error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp.name)

# ========== TTS ENDPOINT ==========
@app.post("/tts")
async def text_to_speech(req: dict, key: str = Depends(verify_key)):
    """Text to speech - uses espeak (no model loading needed)"""
    import subprocess
    import tempfile
    from fastapi.responses import FileResponse
    
    text = req.get('text', '')
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    
    try:
        logger.info(f"🔊 Generating speech for: {text[:50]}...")
        cmd = f'espeak "{text}" -w {tmp.name} -s 150 -v en'
        subprocess.run(cmd, shell=True, check=True, timeout=10)
        
        return FileResponse(tmp.name, media_type="audio/wav", filename="speech.wav")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="TTS timeout")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")

# ========== MODELS INFO ==========
@app.get("/models")
async def list_models(key: str = Depends(verify_key)):
    """List all available models and their loading status"""
    whisper_status = "loaded" if 'get_whisper_model' in dir() and get_whisper_model.cache_info().currsize > 0 else "not loaded"
    translator_status = "loaded" if 'get_translator_model' in dir() and get_translator_model.cache_info().currsize > 0 else "not loaded"
    
    return {
        "endpoints": {
            "/chat": "phi3:mini (loads on first chat)",
            "/code": "deepseek-coder:1.3b (loads on first code)",
            "/stt": "Whisper tiny (loads on first STT call)",
            "/tts": "espeak (always ready)",
            "/translate": "Helsinki-NLP (loads on first translate)",
            "/image": "moondream (loads on first image)",
            "/health": "check all services",
            "/models": "this list"
        },
        "loading_status": {
            "whisper": whisper_status,
            "translator": translator_status
        }
    }