from fastapi import APIRouter, Depends
from pydantic import BaseModel
import time
import logging
from app.config import config
from app.utils.ollama_helper import ollama_helper
from app.utils.cache_helper import cache_helper
from app.routes.auth import verify_key

logger = logging.getLogger(__name__)
router = APIRouter()

class CodeRequest(BaseModel):
    message: str
    language: str = "python"
    use_cache: bool = True

@router.post("/code")
async def code(req: CodeRequest, key: str = Depends(verify_key)):
    """Generate code - deepseek-coder loads on FIRST request only"""
    start = time.time()
    
    # Check cache first
    if req.use_cache and config.CACHE_ENABLED:
        cached = await cache_helper.get("code", req.message, req.language)
        if cached:
            logger.info(f"✅ Code cache hit")
            return {
                **cached,
                "model": config.CODE_MODEL,
                "time_sec": round(time.time() - start, 2),
                "cached": True
            }
    
    # Generate new code (model loads here on first use)
    logger.info(f"🤖 Generating code with {config.CODE_MODEL} (loads now if first time)...")
    prompt = f"Write {req.language} code: {req.message}\nOnly output code, no explanations:"
    reply = await ollama_helper.generate(config.CODE_MODEL, prompt)
    
    result = {
        "code": reply,
        "language": req.language,
        "model": config.CODE_MODEL,
        "time_sec": round(time.time() - start, 2),
        "cached": False
    }
    
    # Cache result
    if config.CACHE_ENABLED:
        await cache_helper.set("code", result, req.message, req.language)
    
    return result