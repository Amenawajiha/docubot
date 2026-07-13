"""
Tests: POST /api/v1/auth/verify-email
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import get_verification_token


@pytest.mark.asyncio
async def test_verify_email_success(client: AsyncClient, db_session: AsyncSession):
    """Valid token marks account as verified."""
    await client.post("/api/v1/auth/register", json={
        "email": "verify@gmail.com", "password": "Password1"
    })
    token = await get_verification_token(db_session, "verify@gmail.com")

    r = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 200
    assert r.json()["email_verified"] is True


@pytest.mark.asyncio
async def test_verify_email_clears_token(client: AsyncClient, db_session: AsyncSession):
    """Token is cleared from DB after successful verification."""
    from sqlalchemy import select
    from app.data.models import User

    await client.post("/api/v1/auth/register", json={
        "email": "cleartoken@gmail.com", "password": "Password1"
    })
    token = await get_verification_token(db_session, "cleartoken@gmail.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    result = await db_session.execute(
        select(User.email_verification_token).where(User.email == "cleartoken@gmail.com")
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_verify_email_invalid_token(client: AsyncClient):
    """Invalid token returns 400."""
    r = await client.post("/api/v1/auth/verify-email", json={"token": "badtoken"})
    assert r.status_code == 400
    assert "invalid" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_email_already_verified(client: AsyncClient, db_session: AsyncSession):
    """
    Re-using an already-consumed token returns 400
    (token is cleared after first use).
    """
    await client.post("/api/v1/auth/register", json={
        "email": "reuse@gmail.com", "password": "Password1"
    })
    token = await get_verification_token(db_session, "reuse@gmail.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    r2 = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_verify_email_expired_token(
    client: AsyncClient, db_session: AsyncSession
):
    """Expired verification token returns 400."""
    from datetime import datetime, timezone
    from sqlalchemy import update
    from app.data.models import User

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

    r = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower()