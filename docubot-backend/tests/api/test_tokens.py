"""
Tests: POST /api/v1/auth/refresh
       POST /api/v1/auth/logout
       GET  /api/v1/auth/me
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import full_login


# ── /me ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_success(client: AsyncClient, db_session: AsyncSession):
    """Valid access token returns user profile."""
    tokens = await full_login(client, db_session)
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    """Missing Authorization header returns 403."""
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    """Garbage token returns 401."""
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer notavalidtoken"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_wrong_token_type(client: AsyncClient, db_session: AsyncSession):
    """Passing a refresh token as Bearer returns 401 (wrong type claim)."""
    tokens = await full_login(client, db_session)
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['refresh_token']}"},
    )
    assert r.status_code == 401


# ── /refresh ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient, db_session: AsyncSession):
    """Valid refresh token returns new token pair."""
    tokens = await full_login(client, db_session)
    r = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"]
    })
    assert r.status_code == 200
    new_tokens = r.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    # New tokens should be different strings
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_old_token_blacklisted(client: AsyncClient, db_session: AsyncSession):
    """After refresh, the old refresh token cannot be used again."""
    tokens = await full_login(client, db_session)
    old_refresh = tokens["refresh_token"]

    # Rotate once
    await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

    # Try to use the old one again — must fail
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    """Invalid refresh token returns 401."""
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient, db_session: AsyncSession):
    """Passing an access token to /refresh returns 401 (wrong type claim)."""
    tokens = await full_login(client, db_session)
    r = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["access_token"]  # wrong token type
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_new_access_token_works_after_refresh(
    client: AsyncClient, db_session: AsyncSession
):
    """Access token from rotated pair is accepted by /me."""
    tokens = await full_login(client, db_session)
    r_refresh = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"]
    })
    new_access = r_refresh.json()["access_token"]

    r_me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_access}"},
    )
    assert r_me.status_code == 200


# ── /logout ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, db_session: AsyncSession):
    """Logout returns 200 and blacklists the refresh token."""
    tokens = await full_login(client, db_session)
    r = await client.post("/api/v1/auth/logout", json={
        "refresh_token": tokens["refresh_token"]
    })
    assert r.status_code == 200
    assert "logged out" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_logout_blacklists_refresh_token(
    client: AsyncClient, db_session: AsyncSession
):
    """After logout the refresh token cannot be used."""
    tokens = await full_login(client, db_session)
    await client.post("/api/v1/auth/logout", json={
        "refresh_token": tokens["refresh_token"]
    })
    r = await client.post("/api/v1/auth/refresh", json={
        "refresh_token": tokens["refresh_token"]
    })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_access_token_still_valid_after_logout(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Access token remains valid after logout (it expires naturally).
    Frontend is responsible for deleting it from localStorage.
    This is the expected behaviour for the localStorage strategy.
    """
    tokens = await full_login(client, db_session)
    await client.post("/api/v1/auth/logout", json={
        "refresh_token": tokens["refresh_token"]
    })
    # Access token still works until its TTL
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert r.status_code == 200