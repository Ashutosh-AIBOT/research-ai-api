from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import time
import tempfile
import os
import whisper
from app.config import config
from app.routes.auth import verify_key
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Load Whisper model (pre-downloaded)
whisper_model = None

@router.on_event("startup")
async def load_whisper():
    global whisper_model
    try:
        whisper_model = whisper.load_model(
            config.WHISPER_MODEL,
            download_root=config.WHISPER_CACHE_DIR
        )
        logger.info("✅ Whisper model loaded")
    except Exception as e:
        logger.error(f"❌ Failed to load Whisper: {e}")

@router.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    key: str = Depends(verify_key)
):
    """Convert speech to text using Whisper"""
    start = time.time()
    
    if not whisper_model:
        raise HTTPException(status_code=503, detail="Whisper model not loaded")
    
    # Save uploaded file temporarily
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.write(await file.read())
    tmp.close()
    
    try:
        # Transcribe
        result = whisper_model.transcribe(tmp.name, fp16=False)
        
        return {
            "text": result["text"],
            "language": result["language"],
            "time_sec": round(time.time() - start, 2)
        }
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp.name)
