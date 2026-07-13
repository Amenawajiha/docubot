"""
Auth service — register, verify-email, login, refresh, logout,
forgot-password, reset-password, change-password.
"""

from __future__ import annotations

import logging
from datetime import timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    get_user_id_from_token,
)
from app.data.models import User
from app.data.repositories.user_repo import UserRepository
from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.email.mailer import (
    send_password_reset_email,
    send_verification_email,
)
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
    VerifyEmailRequest,
)
from app.utils.exceptions import (
    BadRequestError,
    ConflictError,
    EmailNotVerifiedError,
    ForbiddenError,
    InactiveAccountError,
    InvalidTokenError,
    UnauthorizedError,
)
from app.utils.security import (
    generate_secure_token,
    hash_password,
    token_expiry,
    verify_password,
)
from app.utils.validation import has_valid_mx

_REFRESH_TTL = settings.refresh_token_expire_days * 86_400  # seconds
_log = logging.getLogger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    # ── Register ──────────────────────────────────────────────────────────────

    async def register(self, data: RegisterRequest) -> UserOut:
        if not has_valid_mx(str(data.email)):
            raise BadRequestError(
                "The email domain does not appear to accept mail. "
                "Please use a different email address."
            )

        if await self.user_repo.email_exists(str(data.email)):
            raise ConflictError("An account with this email already exists.")

        verification_token = generate_secure_token()
        user = await self.user_repo.create(
            email=str(data.email).lower(),
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            email_verified=False,
            email_verification_token=verification_token,
            email_verification_expires_at=token_expiry(hours=24),
        )

        await send_verification_email(
            email=user.email,
            token=verification_token,
            full_name=user.full_name,
        )
        return UserOut.model_validate(user)

    # ── Verify email ──────────────────────────────────────────────────────────

    async def verify_email(self, data: VerifyEmailRequest) -> TokenResponse:
        user = await self.user_repo.get_by_verification_token(data.token)
        if not user:
            raise BadRequestError("Invalid or expired verification token.")

        expires = user.email_verification_expires_at
        if expires and expires.replace(tzinfo=timezone.utc) < _utcnow():
            raise BadRequestError("Verification token has expired. Please register again.")

        await self.user_repo.update(
            user,
            email_verified=True,
            email_verification_token=None,
            email_verification_expires_at=None,
        )
        return await self._issue_tokens(user)

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.user_repo.get_by_email(str(data.email))

        # Single unified error — prevents telling attackers whether the
        # email exists or the password is wrong.
        # Also blocks OAuth-only accounts (no password_hash) from this endpoint.
        if not user or not user.password_hash:
            raise UnauthorizedError("Incorrect email or password.")

        if not verify_password(data.password, user.password_hash):
            raise UnauthorizedError("Incorrect email or password.")

        if not user.is_active:
            raise InactiveAccountError()

        if not user.email_verified:
            raise EmailNotVerifiedError()

        await self.user_repo.touch_last_login(user)
        return await self._issue_tokens(user)

    # ── Refresh ───────────────────────────────────────────────────────────────

    async def refresh(self, data: RefreshTokenRequest) -> TokenResponse:
        user_id = get_user_id_from_token(data.refresh_token, expected_type="refresh")

        # Check Redis blacklist — degrade gracefully if Redis is down
        try:
            redis = await get_redis()
            blacklisted = await redis.get(f"blacklist:refresh:{data.refresh_token[:16]}")
            if blacklisted:
                raise InvalidTokenError()
        except InvalidTokenError:
            raise
        except Exception as exc:
            _log.warning("Redis unavailable for blacklist check: %s", exc)

        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedError()

        # Blacklist old token before issuing new one (token rotation)
        try:
            redis = await get_redis()
            await redis.setex(
                f"blacklist:refresh:{data.refresh_token[:16]}",
                _REFRESH_TTL,
                "1",
            )
        except Exception as exc:
            _log.warning("Redis unavailable for token rotation: %s", exc)

        return await self._issue_tokens(user)

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(self, refresh_token: str) -> None:
        """Blacklist the refresh token. Degrades gracefully if Redis is down."""
        try:
            redis = await get_redis()
            await redis.setex(
                f"blacklist:refresh:{refresh_token[:16]}",
                _REFRESH_TTL,
                "1",
            )
        except Exception as exc:
            _log.warning("Redis unavailable for logout blacklist: %s", exc)

    # ── Forgot password ───────────────────────────────────────────────────────

    async def forgot_password(self, data: ForgotPasswordRequest) -> None:
        user = await self.user_repo.get_by_email(str(data.email))
        # Always return 200 — prevents email enumeration
        if not user or not user.is_active:
            return
        # OAuth-only accounts have no password — silently skip
        if not user.password_hash:
            return

        reset_token = generate_secure_token()
        await self.user_repo.update(
            user,
            password_reset_token=reset_token,
            password_reset_expires_at=token_expiry(hours=1),
        )
        await send_password_reset_email(
            email=user.email,
            token=reset_token,
            full_name=user.full_name,
        )

    # ── Reset password ────────────────────────────────────────────────────────

    async def reset_password(self, data: ResetPasswordRequest) -> None:
        user = await self.user_repo.get_by_reset_token(data.token)
        if not user:
            raise BadRequestError("Invalid or expired reset token.")

        expires = user.password_reset_expires_at
        if expires and expires.replace(tzinfo=timezone.utc) < _utcnow():
            raise BadRequestError("Reset token has expired.")

        await self.user_repo.update(
            user,
            password_hash=hash_password(data.new_password),
            password_reset_token=None,
            password_reset_expires_at=None,
        )

    # ── Change password (authenticated) ──────────────────────────────────────

    async def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        if not user.password_hash:
            raise ForbiddenError("Password change not allowed for OAuth accounts.")
        if not verify_password(data.current_password, user.password_hash):
            raise ForbiddenError("Current password is incorrect.")

        metadata = dict(user.metadata_) if user.metadata_ else {}
        metadata["password_last_changed"] = _utcnow().isoformat()

        await self.user_repo.update(
            user,
            password_hash=hash_password(data.new_password),
            metadata_=metadata,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(user.id)
        refresh_token, _ = create_refresh_token(user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserOut.model_validate(user),
        )


# ── Standalone helper used by FastAPI dependency ──────────────────────────────

async def get_user_from_token(token: str, session: AsyncSession) -> User:
    user_id = get_user_id_from_token(token, expected_type="access")
    user = await UserRepository(session).get_by_id(user_id)
    if not user:
        raise UnauthorizedError()
    if not user.is_active:
        raise InactiveAccountError()
    return user


def _utcnow():
    from datetime import datetime
    return datetime.now(timezone.utc)