"""Authentication middleware.

Supports three modes controlled by AUTH_MODE env var:
- none (default, solo mode): no auth required
- apikey: X-API-Key header validated against AUTH_API_KEYS env var (comma-separated)
- oauth: Bearer token validated against AUTH_JWKS_URL (team mode)
"""

from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

AUTH_MODE = os.getenv("AUTH_MODE", "none")
AUTH_API_KEYS = set(filter(None, os.getenv("AUTH_API_KEYS", "").split(",")))

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    """Represents the authenticated user (or anonymous in solo mode)."""

    def __init__(self, user_id: uuid.UUID | None = None, username: str = "anonymous", role: str = "admin", claims: dict[str, Any] | None = None):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.claims = claims or {}


_ANONYMOUS = CurrentUser()

# Fixed anonymous UUID for solo mode so FK references work consistently
_SOLO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000000")


async def get_current_user(
    request: Request,
    api_key: str | None = Security(_api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer_scheme),
) -> CurrentUser:
    if AUTH_MODE == "none":
        return CurrentUser(user_id=_SOLO_USER_ID, username="solo", role="admin")

    if AUTH_MODE == "apikey":
        if not api_key or api_key not in AUTH_API_KEYS:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return CurrentUser(user_id=_SOLO_USER_ID, username="apikey-user", role="admin")

    if AUTH_MODE == "oauth":
        if not bearer:
            raise HTTPException(status_code=401, detail="Missing bearer token")
        claims = await _validate_jwt(bearer.credentials)
        return CurrentUser(
            user_id=uuid.UUID(claims.get("sub", str(_SOLO_USER_ID))),
            username=claims.get("preferred_username", claims.get("email", "oauth-user")),
            role=claims.get("role", "member"),
            claims=claims,
        )

    raise HTTPException(status_code=500, detail=f"Unknown auth mode: {AUTH_MODE}")


async def _validate_jwt(token: str) -> dict[str, Any]:
    """Validate JWT against JWKS endpoint. Requires PyJWT[crypto]."""
    jwks_url = os.getenv("AUTH_JWKS_URL")
    if not jwks_url:
        raise HTTPException(status_code=500, detail="AUTH_JWKS_URL not configured for OAuth mode")
    try:
        import jwt
        from jwt import PyJWKClient

        client = PyJWKClient(jwks_url)
        signing_key = client.get_signing_key_from_jwt(token)
        audience = os.getenv("AUTH_AUDIENCE", "repotalk")
        return jwt.decode(token, signing_key.key, algorithms=["RS256"], audience=audience)
    except ImportError:
        raise HTTPException(status_code=500, detail="PyJWT[crypto] required for OAuth mode")
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {exc}")


def require_role(*roles: str):
    """Dependency that enforces user role."""
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if AUTH_MODE == "none":
            return user
        if user.role not in roles:
            raise HTTPException(status_code=403, detail=f"Role '{user.role}' not in {roles}")
        return user
    return _check
