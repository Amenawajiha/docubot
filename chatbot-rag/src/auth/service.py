"""Authentication middleware for JWT token validation."""

import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from src.utils.config_loader import get_config
from src.utils.log_helper import logger

load_dotenv()


class AuthMiddleware:
    """Middleware for handling authentication."""

    def __init__(self):
        """
        Initialize auth middleware.
        """
        self.jwt_secret = os.getenv("JWT_SECRET")
        self.jwt_algorithm = get_config("auth.jwt_algorithm")

    def generate_jwt(self, user_id: int, token_usage="access") -> str:
        """
        Create an access or refresh token for the user.

        Args:
            user_id: User ID to create token for
            token_usage: Token usage ('access' or 'refresh')

        Returns:
            JWT token
        """
        logger.info("Generating %s token..", token_usage)
        if token_usage == "access":
            expires_delta = timedelta(
                minutes=get_config("auth.access_jwt_expiration_minutes")
            )
        elif token_usage == "refresh":
            expires_delta = timedelta(
                days=get_config("auth.refresh_jwt_expiration_days")
            )
        else:
            raise ValueError("Invalid token usage")

        payload = {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + expires_delta,
            "token_usage": token_usage,
        }

        encoded_jwt = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

        return encoded_jwt

    def get_current_refresh_user(
        self,
        token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="/login"))],
    ):
        """Get the current user from the refresh token."""
        try:
            logger.info("Decoding refresh token..")
            # guard: ensure jwt_secret is a string/bytes
            if not isinstance(self.jwt_secret, (str, bytes)) or not self.jwt_secret:
                raise RuntimeError("JWT secret not configured or not a string")
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            sub = payload.get("sub")
            if sub is None:
                raise JWTError("Missing subject claim (sub) in token payload")
            
            try:
                user_id: int = int(sub)
            except (ValueError, TypeError) as e:
                raise JWTError(f"Invalid subject claim (sub) in token: {sub}") from e
            
            if user_id <= 0:
                raise JWTError(f"Invalid user ID in token.")
            
            if payload.get("token_usage") != "refresh":
                raise JWTError("Invalid Token usage. Refresh token expected")
            
            return {"user_id": user_id}
        
        except JWTError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    def get_current_user(
        self,
        token: Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="/login"))],
    ):
        """Get the current user from the token."""
        try:
            logger.info("Decoding access token..")
            # guard: ensure jwt_secret is a string/bytes
            if not isinstance(self.jwt_secret, (str, bytes)) or not self.jwt_secret:
                raise RuntimeError("JWT secret not configured or not a string")
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )
            sub = payload.get("sub")
            if sub is None:
                raise JWTError("Missing subject claim (sub) in token payload")

            try:
                user_id: int = int(sub)
            except (ValueError, TypeError) as e:
                raise JWTError(f"Invalid subject claim (sub) in token: {sub}") from e

            if user_id <= 0:
                raise JWTError("Invalid user ID in token")

            if payload.get("token_usage") != "access":
                raise JWTError("Invalid Token usage. Access token expected")

            return user_id
        except JWTError as e:
            logger.exception(e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate user",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
