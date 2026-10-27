"""
PostureCare Authentication - API Key Validation
Simple API key authentication middleware for GraphQL API
"""

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os
from typing import Set

# Load API keys from environment
ALLOWED_API_KEYS: Set[str] = set()

def _load_api_keys():
    """Load allowed API keys from environment"""
    global ALLOWED_API_KEYS
    keys_str = os.getenv("GRAPHQL_API_KEYS", "test-key-123,dev-key-456")
    ALLOWED_API_KEYS = set(k.strip() for k in keys_str.split(",") if k.strip())
    print(f"✅ Loaded {len(ALLOWED_API_KEYS)} API keys")

# Load keys at module import
_load_api_keys()


class APIKeyMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API keys in request headers"""

    # Public endpoints that don't require authentication
    PUBLIC_ENDPOINTS = {
        "/health",
        "/metrics",
        "/",
        "/docs",
        "/openapi.json",
        "/graphql",  # GraphQL endpoint - auth checked inside resolver
    }

    async def dispatch(self, request: Request, call_next):
        """Validate API key for protected endpoints"""

        # Allow public endpoints
        if request.url.path in self.PUBLIC_ENDPOINTS:
            # For GraphQL, we'll check auth in resolvers
            if request.url.path == "/graphql":
                # Store in request state for use in resolvers
                api_key = request.headers.get("X-API-Key")
                request.state.api_key = api_key
                request.state.is_authenticated = api_key in ALLOWED_API_KEYS if api_key else False
            return await call_next(request)

        # Check API key for protected endpoints
        api_key = request.headers.get("X-API-Key")

        if not api_key:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Missing X-API-Key header",
                },
            )

        if api_key not in ALLOWED_API_KEYS:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Unauthorized",
                    "message": "Invalid API key",
                },
            )

        # Store auth info in request state
        request.state.api_key = api_key
        request.state.is_authenticated = True

        return await call_next(request)


def require_auth(func):
    """Decorator to require authentication in GraphQL resolvers"""
    async def wrapper(self, info, *args, **kwargs):
        # Get request from GraphQL context
        request = info.context.get("request")
        if not request:
            raise HTTPException(status_code=401, detail="No request context")

        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key not in ALLOWED_API_KEYS:
            raise HTTPException(status_code=401, detail="Unauthorized")

        return await func(self, info, *args, **kwargs)

    return wrapper


def get_api_key_from_context(info) -> str:
    """Extract API key from GraphQL context"""
    request = info.context.get("request")
    if request:
        return request.headers.get("X-API-Key", "")
    return ""


def is_authenticated(info) -> bool:
    """Check if request is authenticated"""
    request = info.context.get("request")
    if request:
        api_key = request.headers.get("X-API-Key")
        return api_key in ALLOWED_API_KEYS if api_key else False
    return False
