from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import time
import torch
from transformers import MarianMTModel, MarianTokenizer
from app.config import config
from app.routes.auth import verify_key
from app.utils.cache_helper import cache_helper
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Load translator models (pre-downloaded)
tokenizer = None
model = None

@router.on_event("startup")
async def load_translator():
    global tokenizer, model
    try:
        tokenizer = MarianTokenizer.from_pretrained(config.TRANSLATOR_CACHE_DIR)
        model = MarianMTModel.from_pretrained(config.TRANSLATOR_CACHE_DIR)
        logger.info("✅ Translator model loaded")
    except Exception as e:
        logger.error(f"❌ Failed to load translator: {e}")

class TranslateRequest(BaseModel):
    text: str

@router.post("/translate")
async def translate(req: TranslateRequest, key: str = Depends(verify_key)):
    """Translate Hindi to English"""
    start = time.time()
    
    if not model or not tokenizer:
        raise HTTPException(status_code=503, detail="Translator model not loaded")
    
    async def translate_text():
        try:
            tokens = tokenizer([req.text], return_tensors="pt", padding=True)
            translated = model.generate(**tokens, max_length=128)
            result = tokenizer.decode(translated[0], skip_special_tokens=True)
            return {"translated": result}
        except Exception as e:
            logger.error(f"Translation error: {e}")
            raise
    
    result = await cache_helper.get_or_compute(
        "translate",
        translate_text,
        config.REDIS_TTL,
        req.text
    )
    
    return {
        **result,
        "original": req.text,
        "time_sec": round(time.time() - start, 2),
        "cached": "cached" in result
    }
