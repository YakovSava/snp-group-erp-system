from fastapi import Header, HTTPException, status

from .config import get_settings


def require_service_token(x_service_token: str = Header(default="")) -> None:
    settings = get_settings()
    if not x_service_token or x_service_token != settings.service_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service token")
