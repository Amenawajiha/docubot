"""
JWT encode / decode for access and refresh tokens.

Token payload structure
-----------------------
Access token:
    sub   : str(user_id)
    type  : "access"
    exp   : unix timestamp
    iat   : unix timestamp

Refresh token:
    sub   : str(user_id)
    type  : "refresh"
    jti   : unique token id  (used for Redis blacklist on logout)
    exp   : unix timestamp
    iat   : unix timestamp
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from jose import JWTError, jwt

from app.config import settings
from app.utils.exceptions import InvalidTokenError, TokenExpiredError

TokenType = Literal["access", "refresh"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: uuid.UUID) -> str:
    expire = _now() + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "iat": _now(),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: uuid.UUID) -> tuple[str, str]:
    """Returns (encoded_token, jti) — jti is stored in Redis for blacklist checks."""
    jti = str(uuid.uuid4())
    expire = _now() + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": jti,
        "iat": _now(),
        "exp": expire,
    }
    token = jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return token, jti


def decode_token(token: str, expected_type: TokenType) -> dict:
    """
    Decode and validate a JWT.

    Raises:
        TokenExpiredError  — if the token has passed its expiry
        InvalidTokenError  — for any other JWT issue or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        # jose raises ExpiredSignatureError (subclass of JWTError) for expired tokens
        if "expired" in str(exc).lower():
            raise TokenExpiredError()
        raise InvalidTokenError()

    if payload.get("type") != expected_type:
        raise InvalidTokenError()

    return payload


def get_user_id_from_token(token: str, expected_type: TokenType = "access") -> uuid.UUID:
    payload = decode_token(token, expected_type)
    try:
        return uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise InvalidTokenError()