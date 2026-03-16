from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import tempfile
import subprocess
import os
import hashlib
from app.redis_client import redis_client
from app.routes.auth import verify_key
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Simple in-memory TTS cache
tts_cache = {}

class TTSRequest(BaseModel):
    text: str
    voice: str = "default"

@router.post("/tts")
async def text_to_speech(req: TTSRequest, key: str = Depends(verify_key)):
    """Convert text to speech using espeak (ultra-fast)"""
    
    # Generate cache key
    cache_key = hashlib.md5(req.text.encode()).hexdigest()
    
    # Check memory cache
    if cache_key in tts_cache and os.path.exists(tts_cache[cache_key]):
        return FileResponse(
            tts_cache[cache_key],
            media_type="audio/wav",
            filename="speech.wav"
        )
    
    # Check Redis cache
    cached_path = await redis_client.get(f"tts:{cache_key}")
    if cached_path and os.path.exists(cached_path):
        tts_cache[cache_key] = cached_path
        return FileResponse(cached_path, media_type="audio/wav", filename="speech.wav")
    
    # Generate new audio
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    
    try:
        # Use espeak (ultra-fast, no model needed)
        cmd = f'espeak "{req.text}" -w {tmp.name} -s 150 -v en'
        subprocess.run(cmd, shell=True, check=True, timeout=10)
        
        # Cache the file path
        tts_cache[cache_key] = tmp.name
        await redis_client.set(f"tts:{cache_key}", tmp.name, ttl=3600)
        
        return FileResponse(tmp.name, media_type="audio/wav", filename="speech.wav")
        
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="TTS generation timeout")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
