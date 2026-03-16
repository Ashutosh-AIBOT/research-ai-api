from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import tempfile
import os
import logging
from app.config import config
from app.routes.auth import verify_key

logger = logging.getLogger(__name__)
router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    voice: str = "en"

@router.post("/tts")
async def text_to_speech(req: TTSRequest, key: str = Depends(verify_key)):
    """Text to speech - uses espeak (no model loading needed)"""
    text = req.text
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    
    try:
        logger.info(f"🔊 Generating speech for: {text[:50]}...")
        
        # Use espeak (fast, no model loading)
        cmd = f'espeak "{text}" -w {tmp.name} -s 150 -v {req.voice}'
        subprocess.run(cmd, shell=True, check=True, timeout=10, capture_output=True)
        
        return FileResponse(
            tmp.name, 
            media_type="audio/wav", 
            filename="speech.wav",
            headers={"Content-Disposition": "attachment; filename=speech.wav"}
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="TTS timeout")
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")