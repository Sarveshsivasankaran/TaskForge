"""API Rate limiting configuration using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request


def get_rate_limit_key(request: Request) -> str:
    """
    Determines rate limit key: extracts authenticated user ID if present,
    otherwise falls back to client IP address.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        # Use partial token hash as key to avoid decoding full token twice
        token = auth_header[7:]
        return f"token:{hash(token)}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=["120/minute"],
    storage_uri="memory://"
)
