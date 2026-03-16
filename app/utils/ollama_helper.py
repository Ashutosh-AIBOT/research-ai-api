import ollama
import asyncio
from app.config import config
import logging

logger = logging.getLogger(__name__)

class OllamaHelper:
    def __init__(self):
        self.models = {
            "chat": config.CHAT_MODEL,
            "code": config.CODE_MODEL,
            "image": config.IMAGE_MODEL
        }
        self.cache = {}
    
    async def generate(self, model_type: str, prompt: str, stream: bool = False):
        """Generate response from Ollama"""
        model = self.models.get(model_type)
        if not model:
            raise ValueError(f"Unknown model type: {model_type}")
        
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            
            if stream:
                # For streaming, return generator
                def stream_gen():
                    stream = ollama.chat(
                        model=model,
                        messages=[{'role': 'user', 'content': prompt}],
                        stream=True
                    )
                    for chunk in stream:
                        yield chunk['message']['content']
                
                return stream_gen
            else:
                # For non-streaming, return full response
                response = await loop.run_in_executor(
                    None,
                    lambda: ollama.chat(
                        model=model,
                        messages=[{'role': 'user', 'content': prompt}]
                    )
                )
                return response['message']['content']
                
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise
    
    async def generate_with_images(self, prompt: str, images: list):
        """Generate with images (for moondream)"""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ollama.generate(
                    model=self.models["image"],
                    prompt=prompt,
                    images=images
                )
            )
            return response['response']
        except Exception as e:
            logger.error(f"Ollama image error: {e}")
            raise
    
    def list_models(self):
        """List available models"""
        try:
            return ollama.list()
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return {"models": []}

ollama_helper = OllamaHelper()
