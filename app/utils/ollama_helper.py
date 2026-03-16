import httpx
import asyncio
import logging
from typing import AsyncGenerator, Optional
from app.config import config

logger = logging.getLogger(__name__)

class OllamaHelper:
    def __init__(self):
        # FIXED: Use 127.0.0.1 instead of localhost (prevents DNS resolution issues)
        self.base_url = "http://127.0.0.1:11434"
        
        # Create client with proper timeouts and retries
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.REQUEST_TIMEOUT, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self._model_cache = {}  # Track loaded models
        
        # Add connection test on init
        logger.info(f"🔧 OllamaHelper initialized with base_url: {self.base_url}")
    
    async def _check_connection(self):
        """Test connection to Ollama"""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags", timeout=5.0)
            if response.status_code == 200:
                models = response.json().get('models', [])
                logger.info(f"✅ Ollama connection successful. Available models: {[m['name'] for m in models]}")
                return True
            else:
                logger.error(f"❌ Ollama connection failed with status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to Ollama at {self.base_url}: {e}")
            return False
    
    async def generate(self, model: str, prompt: str) -> str:
        """Generate response (model loads on first use)"""
        try:
            # Log attempt
            logger.info(f"🔄 Generating with model {model}")
            
            # Check if model exists in cache (optional)
            if model not in self._model_cache:
                logger.info(f"📥 First use of {model} - checking availability...")
                # Verify model exists
                try:
                    tags_response = await self.client.get(f"{self.base_url}/api/tags", timeout=5.0)
                    if tags_response.status_code == 200:
                        available_models = [m['name'] for m in tags_response.json().get('models', [])]
                        if model not in available_models:
                            # Try with :latest suffix
                            model_with_latest = f"{model}:latest"
                            if model_with_latest in available_models:
                                model = model_with_latest
                                logger.info(f"✅ Using {model} instead")
                            else:
                                logger.error(f"❌ Model {model} not found in: {available_models}")
                                raise Exception(f"Model {model} not found")
                except Exception as e:
                    logger.warning(f"Could not verify models: {e}")
                
                self._model_cache[model] = True
            
            # Make the actual generation request
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
            
            # Check response
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Ollama error response: {response.status_code} - {error_text}")
                response.raise_for_status()
            
            result = response.json()
            return result["response"]
            
        except httpx.ConnectError as e:
            logger.error(f"🚨 Connection error to Ollama at {self.base_url}: {e}")
            # Try alternative port or localhost as fallback
            logger.info("🔄 Attempting fallback connection to localhost...")
            try:
                fallback_response = await httpx.AsyncClient(timeout=5.0).post(
                    "http://localhost:11434/api/generate",
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
                if fallback_response.status_code == 200:
                    logger.info("✅ Fallback connection successful!")
                    return fallback_response.json()["response"]
            except:
                pass
            raise Exception(f"Cannot connect to Ollama. Is it running?")
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
                if response.status_code != 200:
                    logger.error(f"Stream error: {response.status_code}")
                    yield f"Error: HTTP {response.status_code}"
                    return
                
                async for line in response.aiter_lines():
                    if line:
                        try:
                            import json
                            data = json.loads(line)
                            if "response" in data:
                                yield data["response"]
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON: {line}")
                            continue
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

# Create singleton instance
ollama_helper = OllamaHelper()

# Optional: Test connection on module load
async def test_connection():
    await asyncio.sleep(2)  # Give Ollama time to start
    await ollama_helper._check_connection()

# Run test in background
asyncio.create_task(test_connection())