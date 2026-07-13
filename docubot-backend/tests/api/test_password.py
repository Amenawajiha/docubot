"""
Tests: POST /api/v1/auth/forgot-password
       POST /api/v1/auth/reset-password
       POST /api/v1/auth/change-password
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import full_login, get_reset_token


# ── /forgot-password ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_always_200(client: AsyncClient):
    """Always returns 200 even when email doesn't exist (anti-enumeration)."""
    r = await client.post("/api/v1/auth/forgot-password", json={
        "email": "ghost@gmail.com"
    })
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_forgot_password_stores_reset_token(
    client: AsyncClient, db_session: AsyncSession
):
    """A reset token is stored in DB for a valid verified user."""
    await full_login(client, db_session, "forgot@gmail.com")
    await client.post("/api/v1/auth/forgot-password", json={"email": "forgot@gmail.com"})
    token = await get_reset_token(db_session, "forgot@gmail.com")
    assert len(token) == 64


@pytest.mark.asyncio
async def test_forgot_password_oauth_user_silently_skipped(
    client: AsyncClient, db_session: AsyncSession
):
    """
    OAuth-only user requesting password reset returns 200 but no token is stored
    (they have no password to reset).
    """
    from app.data.repositories.user_repo import UserRepository

    repo = UserRepository(db_session)
    await repo.create(
        email="oauthforgot@gmail.com",
        password_hash=None,
        email_verified=True,
        oauth_provider="google",
        oauth_provider_id="g-456",
    )
    await db_session.commit()

    r = await client.post("/api/v1/auth/forgot-password", json={
        "email": "oauthforgot@gmail.com"
    })
    assert r.status_code == 200  # no leak

    # No token stored
    from sqlalchemy import select
    from app.data.models import User
    result = await db_session.execute(
        select(User.password_reset_token).where(User.email == "oauthforgot@gmail.com")
    )
    assert result.scalar_one_or_none() is None


# ── /reset-password ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reset_password_success(client: AsyncClient, db_session: AsyncSession):
    """Valid reset token lets user set a new password."""
    await full_login(client, db_session, "reset@gmail.com")
    await client.post("/api/v1/auth/forgot-password", json={"email": "reset@gmail.com"})
    token = await get_reset_token(db_session, "reset@gmail.com")

    r = await client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": "NewPassword2",
    })
    assert r.status_code == 200
    assert "reset successfully" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_reset_password_can_login_with_new_password(
    client: AsyncClient, db_session: AsyncSession
):
    """After reset, user can login with new password."""
    await full_login(client, db_session, "resetnew@gmail.com")
    await client.post("/api/v1/auth/forgot-password", json={"email": "resetnew@gmail.com"})
    token = await get_reset_token(db_session, "resetnew@gmail.com")
    await client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "NewPassword2"
    })

    r = await client.post("/api/v1/auth/login", json={
        "email": "resetnew@gmail.com", "password": "NewPassword2"
    })
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reset_password_old_password_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    """After reset, old password no longer works."""
    await full_login(client, db_session, "oldpass@gmail.com")
    await client.post("/api/v1/auth/forgot-password", json={"email": "oldpass@gmail.com"})
    token = await get_reset_token(db_session, "oldpass@gmail.com")
    await client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "NewPassword2"
    })

    r = await client.post("/api/v1/auth/login", json={
        "email": "oldpass@gmail.com", "password": "Password1"  # original
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient):
    """Invalid token returns 400."""
    r = await client.post("/api/v1/auth/reset-password", json={
        "token": "badtoken", "new_password": "NewPassword2"
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reset_token_cleared_after_use(
    client: AsyncClient, db_session: AsyncSession
):
    """Reset token is deleted after successful reset — can't reuse it."""
    await full_login(client, db_session, "clearreset@gmail.com")
    await client.post("/api/v1/auth/forgot-password", json={"email": "clearreset@gmail.com"})
    token = await get_reset_token(db_session, "clearreset@gmail.com")
    await client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "NewPassword2"
    })

    r = await client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "AnotherPass3"
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_expired_token(
    client: AsyncClient, db_session: AsyncSession
):
    """Expired reset token returns 400."""
    from datetime import datetime, timezone
    from sqlalchemy import update
    from app.data.models import User

    await full_login(client, db_session, "expiredreset@gmail.com")
    await client.post("/api/v1/auth/forgot-password", json={"email": "expiredreset@gmail.com"})
    token = await get_reset_token(db_session, "expiredreset@gmail.com")

    await db_session.execute(
        update(User)
        .where(User.email == "expiredreset@gmail.com")
        .values(password_reset_expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
    )
    await db_session.commit()

    r = await client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "NewPassword2"
    })
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reset_password_weak_new_password(
    client: AsyncClient, db_session: AsyncSession
):
    """Weak new_password is rejected with 422."""
    await full_login(client, db_session, "weakreset@gmail.com")
    await client.post("/api/v1/auth/forgot-password", json={"email": "weakreset@gmail.com"})
    token = await get_reset_token(db_session, "weakreset@gmail.com")

    r = await client.post("/api/v1/auth/reset-password", json={
        "token": token, "new_password": "weakpassword"  # no digit, no uppercase
    })
    assert r.status_code == 422


# ── /change-password ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_change_password_success(client: AsyncClient, db_session: AsyncSession):
    """Authenticated user can change their password."""
    tokens = await full_login(client, db_session, "change@gmail.com")
    r = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"current_password": "Password1", "new_password": "Changed2Password"},
    )
    assert r.status_code == 200
    assert "changed" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_change_password_wrong_current(
    client: AsyncClient, db_session: AsyncSession
):
    """Wrong current password returns 403."""
    tokens = await full_login(client, db_session, "changefail@gmail.com")
    r = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"current_password": "WrongPass1", "new_password": "NewPassword2"},
    )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient):
    """Unauthenticated change-password returns 403."""
    r = await client.post("/api/v1/auth/change-password", json={
        "current_password": "Password1", "new_password": "NewPassword2"
    })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_change_password_oauth_user_rejected(
    client: AsyncClient, db_session: AsyncSession
):
    """OAuth-only user (no password_hash) gets 403 on change-password."""
    from app.data.repositories.user_repo import UserRepository
    from app.core.auth.jwt_handler import create_access_token

    repo = UserRepository(db_session)
    user = await repo.create(
        email="oauthchange@gmail.com",
        password_hash=None,
        email_verified=True,
        oauth_provider="github",
        oauth_provider_id="gh-789",
    )
    await db_session.commit()

    access_token = create_access_token(user.id)
    r = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"current_password": "anything", "new_password": "NewPassword2"},
    )
    assert r.status_code == 403
    assert "social login" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_password_can_login_with_new(
    client: AsyncClient, db_session: AsyncSession
):
    """After change, login works with new password and fails with old."""
    tokens = await full_login(client, db_session, "changelogin@gmail.com")
    await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={"current_password": "Password1", "new_password": "NewPassword2"},
    )

    good = await client.post("/api/v1/auth/login", json={
        "email": "changelogin@gmail.com", "password": "NewPassword2"
    })
    assert good.status_code == 200

    bad = await client.post("/api/v1/auth/login", json={
        "email": "changelogin@gmail.com", "password": "Password1"
    })
    assert bad.status_code == 401