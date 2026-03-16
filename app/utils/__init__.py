import httpx
import asyncio
import logging
from typing import AsyncGenerator, Optional
from app.config import config

logger = logging.getLogger(__name__)

class OllamaHelper:
    def __init__(self):
        self.base_url = "http://127.0.0.1:11434"
        self.client = httpx.AsyncClient(timeout=config.REQUEST_TIMEOUT)
        self._model_cache = {}  # Track loaded models
        logger.info(f"🔧 OllamaHelper initialized with base_url: {self.base_url}")
        # Run model check after delay
        asyncio.create_task(self._delayed_model_check())  # ← PASTE THIS LINE HERE
    
    # ← PASTE THE NEW METHOD RIGHT HERE (after __init__, before other methods)
    async def _delayed_model_check(self):
        """Check models after startup"""
        await asyncio.sleep(5)
        await self.ensure_models_available()
    
    async def ensure_models_available(self):
        """Force Ollama to recognize pre-downloaded models"""
        try:
            # First check what models Ollama sees
            response = await self.client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                logger.info(f"📋 Ollama sees: {[m['name'] for m in models]}")
                
                # If no models, try to register them
                if not models:
                    logger.info("🔄 No models found - attempting to register pre-downloaded models...")
                    # The models are in /app/models/ollama/blobs/
                    import os
                    blobs_dir = "/app/models/ollama/blobs"
                    if os.path.exists(blobs_dir):
                        logger.info(f"📁 Models directory exists: {blobs_dir}")
                        
                        # Try to create a simple model to refresh the registry
                        try:
                            # This should force Ollama to rescan
                            await self.client.post(
                                f"{self.base_url}/api/pull",
                                json={"name": "phi3:mini", "insecure": True}
                            )
                            logger.info("✅ Triggered model refresh")
                        except:
                            pass
        except Exception as e:
            logger.error(f"Error ensuring models: {e}")
    
    async def generate(self, model: str, prompt: str) -> str:
        # ... rest of your existing methods ...