from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import time
import os
import tempfile
import logging
from functools import lru_cache
from app.config import config
from app.routes.auth import verify_key

logger = logging.getLogger(__name__)
router = APIRouter()

# On-demand model loading - loads only when first called
@lru_cache(maxsize=1)
def get_whisper_model():
    """Load Whisper model only on first request"""
    logger.info("📥 Loading Whisper model (first time only)...")
    import whisper
    start = time.time()
    model = whisper.load_model(config.WHISPER_MODEL, download_root=config.WHISPER_CACHE_DIR)
    logger.info(f"✅ Whisper model loaded in {time.time()-start:.2f}s")
    return model

@router.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    key: str = Depends(verify_key)
):
    """Speech to text - Whisper loads on FIRST request only"""
    start = time.time()
    
    # Load model on demand (only first time)
    whisper_model = get_whisper_model()
    
    # Save uploaded file temporarily
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
            "time_sec": round(time.time() - start, 2)
        }
    except Exception as e:
        logger.error(f"STT error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp.name)