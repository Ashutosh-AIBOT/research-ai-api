from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
import time
import tempfile
import os
import base64
from app.config import config
from app.utils.ollama_helper import ollama_helper
from app.routes.auth import verify_key
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/image")
async def image_understand(
    file: UploadFile = File(...),
    question: str = "What is in this image?",
    key: str = Depends(verify_key)
):
    """Understand images using moondream"""
    start = time.time()
    
    # Save uploaded image
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.write(await file.read())
    tmp.close()
    
    try:
        # Convert to base64
        with open(tmp.name, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        
        # Generate response
        answer = await ollama_helper.generate_with_images(question, [img_b64])
        
        return {
            "answer": answer,
            "question": question,
            "time_sec": round(time.time() - start, 2)
        }
        
    except Exception as e:
        logger.error(f"Image understanding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp.name)

