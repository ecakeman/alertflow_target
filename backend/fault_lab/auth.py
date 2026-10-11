"""Bearer-token helpers shared by the protected endpoints."""

from __future__ import annotations

import hmac
from typing import Optional

from fastapi import Header, HTTPException, status


def parse_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    return token or None


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def check_token(authorization: Optional[str], expected: Optional[str], *, required: bool) -> None:
    """Validate a bearer token.

    ``required`` is True when the endpoint must always be protected (control
    API). For the optional diagnostics token, ``expected`` being falsy means the
    endpoint is open.
    """
    if not expected:
        if required:
            # No control token configured: fail closed rather than open.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="control token is not configured on the server",
            )
        return
    presented = parse_bearer(authorization)
    if presented is None or not hmac.compare_digest(presented, expected):
        raise _unauthorized("invalid or missing bearer token")


def _dependency(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    return authorization
