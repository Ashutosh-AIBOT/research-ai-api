from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time
import json
import asyncio
from app.config import config
from app.redis_client import redis_client
from app.kafka_client import kafka_client
from app.utils.ollama_helper import ollama_helper
from app.utils.cache_helper import cache_helper
from app.routes.auth import verify_key
import logging

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
    """Chat endpoint with Redis caching and optional streaming"""
    start = time.time()
    request_id = f"chat:{int(time.time())}:{hash(req.message)}"
    
    # Stream mode
    if req.stream and config.STREAMING_ENABLED:
        return StreamingResponse(
            stream_chat_response(req.message, req.system, request_id),
            media_type="text/event-stream"
        )
    
    # Cache mode
    if req.use_cache:
        # Try to get from cache
        cached = await cache_helper.get_or_compute(
            "chat",
            generate_chat_response,
            config.REDIS_TTL,
            req.message,
            req.system,
            request_id
        )
        
        if cached:
            return ChatResponse(
                model=config.CHAT_MODEL,
                reply=cached["reply"],
                time_sec=round(time.time() - start, 2),
                cached=True,
                request_id=request_id
            )
    
    # Generate new response
    reply = await generate_chat_response(req.message, req.system, request_id)
    
    return ChatResponse(
        model=config.CHAT_MODEL,
        reply=reply["reply"],
        time_sec=round(time.time() - start, 2),
        cached=False,
        request_id=request_id
    )

async def generate_chat_response(message: str, system: str, request_id: str = None):
    """Generate chat response using Ollama"""
    prompt = f"System: {system}\nUser: {message}\nAssistant:"
    reply = await ollama_helper.generate("chat", prompt)
    
    # Send to Kafka for analytics
    if request_id and config.STREAMING_ENABLED:
        await kafka_client.send_response_chunk(request_id, reply, is_last=True)
    
    return {"reply": reply}

async def stream_chat_response(message: str, system: str, request_id: str):
    """Stream chat response token by token"""
    prompt = f"System: {system}\nUser: {message}\nAssistant:"
    stream_gen = await ollama_helper.generate("chat", prompt, stream=True)
    
    full_response = ""
    for token in stream_gen():
        full_response += token
        yield f"data: {json.dumps({'token': token, 'request_id': request_id})}\n\n"
        await asyncio.sleep(0.01)  # Small delay for smooth streaming
    
    # Cache the full response
    await redis_client.set_json(
        cache_helper.generate_key("chat", message, system),
        {"reply": full_response},
        config.REDIS_TTL
    )
    
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
            
            # Generate streaming response
            prompt = f"System: {req.get('system', 'You are helpful')}\nUser: {req.get('message')}\nAssistant:"
            stream_gen = await ollama_helper.generate("chat", prompt, stream=True)
            
            for token in stream_gen():
                await websocket.send_text(json.dumps({
                    'token': token,
                    'done': False
                }))
            
            await websocket.send_text(json.dumps({'done': True}))
            
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
