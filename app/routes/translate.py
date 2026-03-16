from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import time
import logging
from functools import lru_cache
from app.config import config
from app.routes.auth import verify_key

logger = logging.getLogger(__name__)
router = APIRouter()

class TranslateRequest(BaseModel):
    text: str
    source_lang: str = "hi"
    target_lang: str = "en"

# On-demand model loading - loads only when first called
@lru_cache(maxsize=1)
def get_translator_model():
    """Load Translator model only on first request"""
    logger.info("📥 Loading Translator model (first time only)...")
    from transformers import MarianMTModel, MarianTokenizer
    start = time.time()
    tokenizer = MarianTokenizer.from_pretrained(
        config.TRANSLATOR_MODEL, 
        cache_dir=config.TRANSLATOR_CACHE_DIR
    )
    model = MarianMTModel.from_pretrained(
        config.TRANSLATOR_MODEL, 
        cache_dir=config.TRANSLATOR_CACHE_DIR
    )
    logger.info(f"✅ Translator model loaded in {time.time()-start:.2f}s")
    return tokenizer, model

@router.post("/translate")
async def translate(req: TranslateRequest, key: str = Depends(verify_key)):
    """Translate Hindi to English - model loads on FIRST request only"""
    start = time.time()
    
    # Load model on demand (only first time)
    tokenizer, model = get_translator_model()
    
    text = req.text
    logger.info(f"🔄 Translating: {text[:50]}...")
    
    try:
        tokens = tokenizer([text], return_tensors="pt", padding=True)
        translated = model.generate(**tokens, max_length=128)
        result = tokenizer.decode(translated[0], skip_special_tokens=True)
        
        return {
            "original": text,
            "translated": result,
            "source_lang": req.source_lang,
            "target_lang": req.target_lang,
            "time_sec": round(time.time() - start, 2)
        }
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))