from fastapi import Header, HTTPException, status

from config import get_settings


def require_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    expected = get_settings().admin_token
    if not x_admin_token or x_admin_token != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Admin-Token",
        )
