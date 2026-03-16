from fastapi import APIRouter, Depends
from pydantic import BaseModel
import time
from app.config import config
from app.utils.ollama_helper import ollama_helper
from app.utils.cache_helper import cache_helper
from app.routes.auth import verify_key

router = APIRouter()

class CodeRequest(BaseModel):
    message: str
    language: str = "python"
    use_cache: bool = True

@router.post("/code")
async def code(req: CodeRequest, key: str = Depends(verify_key)):
    """Generate code using deepseek-coder"""
    start = time.time()
    
    async def generate_code():
        prompt = f"Write {req.language} code: {req.message}\nOnly output code, no explanations:"
        reply = await ollama_helper.generate("code", prompt)
        return {"code": reply, "language": req.language}
    
    if req.use_cache:
        result = await cache_helper.get_or_compute(
            "code",
            generate_code,
            config.REDIS_TTL,
            req.message,
            req.language
        )
    else:
        result = await generate_code()
    
    return {
        **result,
        "model": config.CODE_MODEL,
        "time_sec": round(time.time() - start, 2),
        "cached": req.use_cache and "cached" in result
    }
