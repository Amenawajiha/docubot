"""
Tests: POST /api/v1/auth/register
Covers every branch in AuthService.register()
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import get_verification_token


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Valid registration returns 201 with user object."""
    r = await client.post("/api/v1/auth/register", json={
        "email": "alice@gmail.com",
        "password": "Password1",
        "full_name": "Alice Smith",
    })
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "alice@gmail.com"
    assert body["full_name"] == "Alice Smith"
    assert body["email_verified"] is False   # must verify before login
    assert body["is_active"] is True
    assert body["oauth_provider"] is None
    assert "id" in body
    assert "created_at" in body
    # password_hash must NEVER be returned
    assert "password_hash" not in body
    assert "password" not in body


@pytest.mark.asyncio
async def test_register_stores_verification_token(
    client: AsyncClient, db_session: AsyncSession
):
    """A verification token is stored in the DB after registration."""
    await client.post("/api/v1/auth/register", json={
        "email": "bob@gmail.com",
        "password": "Password1",
    })
    token = await get_verification_token(db_session, "bob@gmail.com")
    assert len(token) == 64


@pytest.mark.asyncio
async def test_register_email_case_insensitive(client: AsyncClient):
    """Email is normalised to lowercase."""
    r = await client.post("/api/v1/auth/register", json={
        "email": "Alice@Gmail.COM",
        "password": "Password1",
    })
    assert r.status_code == 201
    assert r.json()["email"] == "alice@gmail.com"


# ── Duplicate email ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Second registration with the same email returns 409."""
    payload = {"email": "dup@gmail.com", "password": "Password1"}
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert "already exists" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_email_case_insensitive(client: AsyncClient):
    """Duplicate check is case-insensitive."""
    await client.post("/api/v1/auth/register", json={
        "email": "dup@gmail.com", "password": "Password1"
    })
    r = await client.post("/api/v1/auth/register", json={
        "email": "DUP@GMAIL.COM", "password": "Password1"
    })
    assert r.status_code == 409


# ── Password validation ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_weak_password_no_uppercase(client: AsyncClient):
    """Password without uppercase letter returns 422."""
    r = await client.post("/api/v1/auth/register", json={
        "email": "weak@gmail.com", "password": "password1",
    })
    assert r.status_code == 422
    assert "uppercase" in r.text.lower()


@pytest.mark.asyncio
async def test_register_weak_password_no_digit(client: AsyncClient):
    """Password without digit returns 422."""
    r = await client.post("/api/v1/auth/register", json={
        "email": "weak@gmail.com", "password": "Password",
    })
    assert r.status_code == 422
    assert "digit" in r.text.lower()


@pytest.mark.asyncio
async def test_register_password_too_short(client: AsyncClient):
    """Password shorter than 8 chars returns 422."""
    r = await client.post("/api/v1/auth/register", json={
        "email": "short@gmail.com", "password": "Px1",
    })
    assert r.status_code == 422


# ── Email format validation ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_invalid_email_format(client: AsyncClient):
    """Malformed email returns 422."""
    r = await client.post("/api/v1/auth/register", json={
        "email": "not-an-email", "password": "Password1",
    })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_fake_domain_rejected(client: AsyncClient):
    """
    Email on a nonexistent domain (no MX records) returns 400.
    We use a clearly invalid domain to guarantee it has no MX records.
    """
    r = await client.post("/api/v1/auth/register", json={
        "email": "user@thisdoesnotexist-xyz-abc-123.io",
        "password": "Password1",
    })
    assert r.status_code == 400
    assert "domain" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_real_domain_accepted(client: AsyncClient):
    """Email on a real domain (gmail.com has MX) passes the domain check."""
    r = await client.post("/api/v1/auth/register", json={
        "email": "test@gmail.com", "password": "Password1",
    })
    # Should reach duplicate/creation stage, not fail on domain
    assert r.status_code in (201, 409)  # 409 if test is run twice