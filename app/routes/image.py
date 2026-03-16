from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
import time
import tempfile
import os
import base64
import logging
from app.config import config
from app.utils.ollama_helper import ollama_helper
from app.routes.auth import verify_key

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/image")
async def image_understand(
    file: UploadFile = File(...),
    question: str = "What is in this image?",
    key: str = Depends(verify_key)
):
    """Image understanding - moondream loads on FIRST request only"""
    start = time.time()
    
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    content = await file.read()
    tmp.write(content)
    tmp.close()
    
    try:
        logger.info(f"🖼️ Analyzing image ({len(content)} bytes) with question: {question}")
        
        with open(tmp.name, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        # This will load moondream on first call
        response = await ollama_helper.generate_with_image(
            config.IMAGE_MODEL, 
            question, 
            img_b64
        )
        
        return {
            "answer": response,
            "time_sec": round(time.time() - start, 2)
        }
    except Exception as e:
        logger.error(f"Image analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp.name)