from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time
import json
import asyncio
import logging
from app.config import config
from app.redis_client import redis_client
from app.kafka_client import kafka_client
from app.utils.ollama_helper import ollama_helper
from app.utils.cache_helper import cache_helper
from app.routes.auth import verify_key

logger = logging.getLogger(__name__)
router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    system: str = "You are a helpful assistant."
    stream: bool = False
    use_cache: bool = True

class ChatResponse(BaseModel):
    model: str
    reply: str
    time_sec: float
    cached: bool = False
    request_id: str = None

@router.post("/chat")
async def chat(req: ChatRequest, key: str = Depends(verify_key)):
    """Chat endpoint - Ollama model loads on FIRST request only"""
    start = time.time()
    request_id = f"chat:{int(time.time())}:{hash(req.message)}"
    
    # Stream mode
    if req.stream and config.STREAMING_ENABLED:
        return StreamingResponse(
            stream_chat_response(req.message, req.system, request_id),
            media_type="text/event-stream"
        )
    
    # Cache mode
    if req.use_cache and config.CACHE_ENABLED:
        # Try to get from cache
        cached = await cache_helper.get("chat", req.message, req.system)
        if cached:
            logger.info(f"✅ Cache hit for: {req.message[:50]}...")
            return ChatResponse(
                model=config.CHAT_MODEL,
                reply=cached["reply"],
                time_sec=round(time.time() - start, 2),
                cached=True,
                request_id=request_id
            )
    
    # Generate new response (model loads here on first use)
    logger.info(f"🤖 Generating chat response (model loads now if first time)...")
    reply = await generate_chat_response(req.message, req.system, request_id)
    
    # Cache the response
    if config.CACHE_ENABLED:
        await cache_helper.set("chat", {"reply": reply}, req.message, req.system)
    
    return ChatResponse(
        model=config.CHAT_MODEL,
        reply=reply,
        time_sec=round(time.time() - start, 2),
        cached=False,
        request_id=request_id
    )

async def generate_chat_response(message: str, system: str, request_id: str = None):
    """Generate chat response using Ollama (loads model on first call)"""
    prompt = f"System: {system}\nUser: {message}\nAssistant:"
    
    # This will load the model on first call automatically
    reply = await ollama_helper.generate(config.CHAT_MODEL, prompt)
    
    # Send to Kafka for analytics (optional)
    if request_id and config.STREAMING_ENABLED and kafka_client.producer:
        await kafka_client.send_response_chunk(request_id, reply, is_last=True)
    
    return reply

async def stream_chat_response(message: str, system: str, request_id: str):
    """Stream chat response token by token"""
    prompt = f"System: {system}\nUser: {message}\nAssistant:"
    
    full_response = ""
    async for token in ollama_helper.generate_stream(config.CHAT_MODEL, prompt):
        full_response += token
        yield f"data: {json.dumps({'token': token, 'request_id': request_id})}\n\n"
        await asyncio.sleep(0.01)
    
    # Cache the full response
    if config.CACHE_ENABLED:
        await cache_helper.set("chat", {"reply": full_response}, message, system)
    
    yield f"data: {json.dumps({'done': True, 'request_id': request_id})}\n\n"

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    # Authenticate
    auth_data = await websocket.receive_text()
    if auth_data != config.API_KEY:
        await websocket.close(code=1008)
        return
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            req = json.loads(data)
            
            logger.info(f"📱 WebSocket chat: {req.get('message', '')[:50]}...")
            
            # Generate streaming response
            prompt = f"System: {req.get('system', 'You are helpful')}\nUser: {req.get('message')}\nAssistant:"
            
            async for token in ollama_helper.generate_stream(config.CHAT_MODEL, prompt):
                await websocket.send_text(json.dumps({
                    'token': token,
                    'done': False
                }))
            
            await websocket.send_text(json.dumps({'done': True}))
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")