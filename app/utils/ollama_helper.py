import httpx
import asyncio
import logging
from typing import AsyncGenerator, Optional
from app.config import config

logger = logging.getLogger(__name__)

class OllamaHelper:
    def __init__(self):
        self.base_url = "http://localhost:11434"
        self.client = httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT)
        self._model_cache = {}  # Track loaded models
    
    async def generate(self, model: str, prompt: str) -> str:
        """Generate response (model loads on first use)"""
        try:
            if model not in self._model_cache:
                logger.info(f"📥 First use of {model} - loading now...")
                self._model_cache[model] = True
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 512,
                        "temperature": 0.7
                    }
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            raise
    
    async def generate_stream(self, model: str, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response token by token"""
        try:
            if model not in self._model_cache:
                logger.info(f"📥 First use of {model} - loading now...")
                self._model_cache[model] = True
            
            async with self.client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "num_predict": 512,
                        "temperature": 0.7
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done", False):
                            break
        except Exception as e:
            logger.error(f"Ollama stream error: {e}")
            yield f"Error: {str(e)}"
    
    async def generate_with_image(self, model: str, prompt: str, image_b64: str) -> str:
        """Generate with image input"""
        try:
            if model not in self._model_cache:
                logger.info(f"📥 First use of {model} - loading now...")
                self._model_cache[model] = True
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            logger.error(f"Ollama image error: {e}")
            raise
    
    async def close(self):
        await self.client.aclose()

ollama_helper = OllamaHelper()