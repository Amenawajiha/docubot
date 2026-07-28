"""
Tests: GET/POST /api/v1/auth/verify-email
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.data.models import User
from tests.conftest import get_verification_token


@pytest.mark.asyncio
async def test_verify_email_success(client: AsyncClient, db_session: AsyncSession):
    """Valid token marks account as verified and redirects to verify-success."""
    await client.post("/api/v1/auth/register", json={
        "email": "verify@gmail.com", "password": "Password1"
    })
    token = await get_verification_token(db_session, "verify@gmail.com")

    r = await client.get(f"/api/v1/auth/verify-email?token={token}", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/verify-success" in r.headers["location"]

    result = await db_session.execute(select(User).where(User.email == "verify@gmail.com"))
    user = result.scalar_one()
    assert user.email_verified is True


@pytest.mark.asyncio
async def test_verify_email_clears_token(client: AsyncClient, db_session: AsyncSession):
    """Token is cleared from DB after successful verification."""
    await client.post("/api/v1/auth/register", json={
        "email": "cleartoken@gmail.com", "password": "Password1"
    })
    token = await get_verification_token(db_session, "cleartoken@gmail.com")
    await client.get(f"/api/v1/auth/verify-email?token={token}")

    result = await db_session.execute(
        select(User.email_verification_token).where(User.email == "cleartoken@gmail.com")
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient):
    """Invalid token redirects to verify-error."""
    r = await client.get("/api/v1/auth/verify-email?token=badtoken", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/verify-error" in r.headers["location"]
    assert "reason=" in r.headers["location"]


@pytest.mark.asyncio
async def test_verify_email_already_verified(client: AsyncClient, db_session: AsyncSession):
    """
    Re-using an already-consumed token redirects to verify-error
    (token is cleared after first use).
    """
    await client.post("/api/v1/auth/register", json={
        "email": "reuse@gmail.com", "password": "Password1"
    })
    token = await get_verification_token(db_session, "reuse@gmail.com")
    await client.get(f"/api/v1/auth/verify-email?token={token}")

    r2 = await client.get(f"/api/v1/auth/verify-email?token={token}", follow_redirects=False)
    assert r2.status_code == 302
    assert "/auth/verify-error" in r2.headers["location"]


@pytest.mark.asyncio
async def test_verify_email_expired_token(
    client: AsyncClient, db_session: AsyncSession
):
    """Expired verification token redirects to verify-error."""
    from datetime import datetime, timezone

    await client.post("/api/v1/auth/register", json={
        "email": "expired@gmail.com", "password": "Password1"
    })
    token = await get_verification_token(db_session, "expired@gmail.com")

    # Backdate the expiry to the past
    await db_session.execute(
        update(User)
        .where(User.email == "expired@gmail.com")
        .values(email_verification_expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc))
    )
    await db_session.commit()

    r = await client.get(f"/api/v1/auth/verify-email?token={token}", follow_redirects=False)
    assert r.status_code == 302
    assert "/auth/verify-error" in r.headers["location"]