from fastapi import HTTPException, Depends
from fastapi.security import APIKeyHeader
from app.config import config

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_key(api_key: str = Depends(api_key_header)):
    """Verify API key"""
    if not api_key or api_key != config.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key"
        )
    return api_key