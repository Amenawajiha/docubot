"""
Tests: POST /api/v1/auth/login
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import full_login, get_verification_token


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    """Verified user gets access + refresh tokens."""
    tokens = await full_login(client, db_session)
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    assert tokens["expires_in"] == 3600
    assert tokens["user"]["email"] == "user@example.com"
    assert tokens["user"]["email_verified"] is True


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    """Wrong password returns 401."""
    await client.post("/api/v1/auth/register", json={
        "email": "wp@gmail.com", "password": "Password1"
    })
    token = await get_verification_token(db_session, "wp@gmail.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    r = await client.post("/api/v1/auth/login", json={
        "email": "wp@gmail.com", "password": "WrongPass1"
    })
    assert r.status_code == 401
    assert "incorrect" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    """Login with email that was never registered returns 401."""
    r = await client.post("/api/v1/auth/login", json={
        "email": "ghost@gmail.com", "password": "Password1"
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unverified_email(client: AsyncClient):
    """User who hasn't verified email gets 403."""
    await client.post("/api/v1/auth/register", json={
        "email": "unverified@gmail.com", "password": "Password1"
    })
    r = await client.post("/api/v1/auth/login", json={
        "email": "unverified@gmail.com", "password": "Password1"
    })
    assert r.status_code == 403
    assert "not verified" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession):
    """Inactive user gets 403."""
    from sqlalchemy import update
    from app.data.models import User

    await full_login(client, db_session, "inactive@gmail.com")
    await db_session.execute(
        update(User).where(User.email == "inactive@gmail.com").values(is_active=False)
    )
    await db_session.commit()

    r = await client.post("/api/v1/auth/login", json={
        "email": "inactive@gmail.com", "password": "Password1"
    })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_login_oauth_user_blocked_from_password_login(
    client: AsyncClient, db_session: AsyncSession
):
    """OAuth-only user (no password_hash) cannot use password login."""
    from app.data.models import User
    from app.data.repositories.user_repo import UserRepository

    repo = UserRepository(db_session)
    await repo.create(
        email="oauthonly@gmail.com",
        password_hash=None,
        full_name="OAuth User",
        email_verified=True,
        oauth_provider="google",
        oauth_provider_id="google-123",
    )
    await db_session.commit()

    r = await client.post("/api/v1/auth/login", json={
        "email": "oauthonly@gmail.com", "password": "Password1"
    })
    assert r.status_code == 401
    assert "incorrect" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_updates_last_login_at(client: AsyncClient, db_session: AsyncSession):
    """last_login_at is set on successful login."""
    from sqlalchemy import select
    from app.data.models import User

    await full_login(client, db_session, "logintime@gmail.com")
    result = await db_session.execute(
        select(User.last_login_at).where(User.email == "logintime@gmail.com")
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_login_password_not_in_response(client: AsyncClient, db_session: AsyncSession):
    """Response never contains password_hash or password."""
    tokens = await full_login(client, db_session)
    assert "password" not in str(tokens)
    assert "hash" not in str(tokens)