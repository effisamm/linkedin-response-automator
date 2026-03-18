from fastapi import Header, HTTPException, status
from app.core.config import settings

async def get_current_client_id(x_api_key: str = Header(...)) -> str:
    """
    Dependency to authenticate and identify a client by their API key.
    """
    if x_api_key in settings.API_KEYS:
        client_id = settings.API_KEYS[x_api_key]
        return client_id
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
