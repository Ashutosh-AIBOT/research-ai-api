# app/utils/ollama_helper.py
import httpx
import asyncio
import logging
import os
import subprocess
from typing import AsyncGenerator
from app.config import config

logger = logging.getLogger(__name__)

class OllamaHelper:
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(config.REQUEST_TIMEOUT, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self._model_cache = {}
        logger.info(f"🔧 OllamaHelper initialized with base_url: {self.base_url}")
        
        # Run model check after startup
        asyncio.create_task(self._delayed_model_check())
    
    async def _delayed_model_check(self):
        """Check models after services are fully started"""
        await asyncio.sleep(10)  # Wait for Ollama to fully initialize
        await self._force_register_models()
        await self.ensure_models_available()
    
    async def _force_register_models(self):
        """Force register models using ollama CLI"""
        try:
            logger.info("🔧 Attempting to force register models via CLI...")
            
            # List of models to register
            models = ["phi3:mini", "deepseek-coder:1.3b", "moondream"]
            
            for model in models:
                try:
                    # Try to create model from existing blobs
                    cmd = f"ollama pull {model}"
                    logger.info(f"🔄 Running: {cmd}")
                    
                    process = await asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0:
                        logger.info(f"✅ Successfully registered {model}")
                        self._model_cache[model] = True
                    else:
                        logger.warning(f"⚠️ Failed to register {model}: {stderr.decode()}")
                        
                except Exception as e:
                    logger.error(f"Error registering {model}: {e}")
                    
        except Exception as e:
            logger.error(f"Force register error: {e}")
    
    async def ensure_models_available(self):
        """Check what models Ollama sees"""
        try:
            logger.info("🔍 Checking available Ollama models...")
            response = await self.client.get(f"{self.base_url}/api/tags")
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    model_names = [m['name'] for m in models]
                    logger.info(f"✅ Ollama models found: {model_names}")
                    
                    # Cache the models
                    for model in model_names:
                        self._model_cache[model] = True
                else:
                    logger.warning("⚠️ No models found in Ollama registry!")
                    
                    # Try one more time with direct file copy approach
                    await self._copy_models_directly()
            else:
                logger.error(f"❌ Failed to get models: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error checking models: {e}")
    
    async def _copy_models_directly(self):
        """Last resort: Try to copy model files directly"""
        try:
            logger.info("📁 Attempting direct model registration...")
            
            # Check if models directory exists
            models_dir = "/app/models/ollama"
            if os.path.exists(models_dir):
                logger.info(f"📁 Models directory found: {models_dir}")
                
                # List contents
                for root, dirs, files in os.walk(models_dir):
                    for file in files:
                        if file.endswith('.bin') or 'blob' in file:
                            logger.info(f"📄 Found model file: {os.path.join(root, file)}")
            
            # Try to create a model manifest
            manifest_dir = f"{models_dir}/manifests/registry.ollama.ai/library"
            os.makedirs(manifest_dir, exist_ok=True)
            
            logger.info("✅ Direct model check complete")
            
        except Exception as e:
            logger.error(f"Direct copy error: {e}")
    
    async def generate(self, model: str, prompt: str) -> str:
        """Generate response with automatic model loading"""
        try:
            logger.info(f"🔄 Generating with model {model}")
            
            # If model not in cache, try to load it
            if model not in self._model_cache:
                logger.info(f"📥 Model {model} not in cache, attempting to load...")
                
                # Try to pull the model first
                try:
                    pull_response = await self.client.post(
                        f"{self.base_url}/api/pull",
                        json={"name": model, "insecure": True}
                    )
                    if pull_response.status_code == 200:
                        logger.info(f"✅ Successfully pulled {model}")
                        self._model_cache[model] = True
                except Exception as pull_error:
                    logger.warning(f"Pull failed, but may already exist: {pull_error}")
            
            # Generate response
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
            
            if response.status_code != 200:
                error_text = await response.aread()
                logger.error(f"Ollama error: {response.status_code} - {error_text}")
                
                # If model not found, try with :latest suffix
                if "not found" in error_text.decode():
                    model_with_latest = f"{model}:latest"
                    logger.info(f"🔄 Retrying with {model_with_latest}")
                    
                    response = await self.client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": model_with_latest,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "num_predict": 512,
                                "temperature": 0.7
                            }
                        }
                    )
                    if response.status_code == 200:
                        result = response.json()
                        return result["response"]
                
                response.raise_for_status()
            
            result = response.json()
            return result["response"]
            
        except Exception as e:
            logger.error(f"Ollama generate error: {e}")
            raise
    
    async def generate_stream(self, model: str, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response token by token"""
        try:
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
                            continue
        except Exception as e:
            logger.error(f"Stream error: {e}")
            yield f"Error: {str(e)}"
    
    async def generate_with_image(self, model: str, prompt: str, image_b64: str) -> str:
        """Generate with image input"""
        try:
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
            logger.error(f"Image error: {e}")
            raise
    
    async def close(self):
        await self.client.aclose()

# Create singleton instance
ollama_helper = OllamaHelper()