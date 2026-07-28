"""
Tests: POST /api/v1/auth/refresh
       POST /api/v1/auth/logout
       GET  /api/v1/auth/me

All tests conform to the HttpOnly Cookie API contract:
- Cookies set on login/refresh: 'access_token' and 'refresh_token'
- /me reads access_token from cookies or Authorization Bearer header
- /refresh and /logout read refresh_token from cookies (or optional JSON body)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.jwt_handler import create_refresh_token
from tests.conftest import full_login


# ── /me ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_success(client: AsyncClient, db_session: AsyncSession):
    """Valid access_token cookie returns user profile."""
    await full_login(client, db_session)
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "user@example.com"


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    """Missing access_token cookie and header returns 401."""
    client.cookies.clear()
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    """Garbage token returns 401."""
    client.cookies.clear()
    client.cookies.set("access_token", "notavalidtoken")
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_wrong_token_type(client: AsyncClient, db_session: AsyncSession):
    """Passing a refresh token in access_token cookie returns 401 (wrong type claim)."""
    user_data = await full_login(client, db_session)
    user_id = user_data["user"]["id"]
    refresh_jwt, _ = create_refresh_token(user_id)

    client.cookies.clear()
    client.cookies.set("access_token", refresh_jwt)
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


# ── /refresh ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient, db_session: AsyncSession):
    """Valid refresh token cookie rotates tokens and updates cookies."""
    await full_login(client, db_session)
    old_refresh = client.cookies.get("refresh_token")
    old_access = client.cookies.get("access_token")

    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 200

    new_refresh = client.cookies.get("refresh_token")
    new_access = client.cookies.get("access_token")

    assert new_access is not None and new_access != ""
    assert new_refresh is not None and new_refresh != ""
    assert new_access != old_access
    assert new_refresh != old_refresh


@pytest.mark.asyncio
async def test_refresh_old_token_blacklisted(client: AsyncClient, db_session: AsyncSession):
    """After refresh, the old refresh token cannot be used again."""
    await full_login(client, db_session)
    old_refresh = client.cookies.get("refresh_token")
    assert old_refresh is not None

    # Rotate once
    await client.post("/api/v1/auth/refresh")

    # Try to use the old refresh token again — must fail
    client.cookies.set("refresh_token", old_refresh)
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    """Invalid refresh token returns 401."""
    client.cookies.clear()
    client.cookies.set("refresh_token", "garbage")
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient, db_session: AsyncSession):
    """Passing an access token as refresh_token returns 401 (wrong type claim)."""
    await full_login(client, db_session)
    access_token = client.cookies.get("access_token")
    assert access_token is not None

    client.cookies.set("refresh_token", access_token)
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_new_access_token_works_after_refresh(
    client: AsyncClient, db_session: AsyncSession
):
    """Access token cookie from rotated pair is accepted by /me."""
    await full_login(client, db_session)
    r_refresh = await client.post("/api/v1/auth/refresh")
    assert r_refresh.status_code == 200

    r_me = await client.get("/api/v1/auth/me")
    assert r_me.status_code == 200


# ── /logout ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient, db_session: AsyncSession):
    """Logout returns 200, blacklists refresh token, and clears cookies."""
    await full_login(client, db_session)
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert "logged out" in r.json()["message"].lower()
    assert "access_token" not in client.cookies or client.cookies.get("access_token") == ""


@pytest.mark.asyncio
async def test_logout_blacklists_refresh_token(
    client: AsyncClient, db_session: AsyncSession
):
    """After logout the refresh token cannot be used."""
    await full_login(client, db_session)
    old_refresh = client.cookies.get("refresh_token")
    assert old_refresh is not None

    await client.post("/api/v1/auth/logout")

    # Attempt refresh using logged-out token
    client.cookies.set("refresh_token", old_refresh)
    r = await client.post("/api/v1/auth/refresh")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_access_token_still_valid_after_logout(
    client: AsyncClient, db_session: AsyncSession
):
    """
    Access token remains valid if passed explicitly via Bearer header after logout
    (it expires naturally by TTL).
    """
    await full_login(client, db_session)
    old_access = client.cookies.get("access_token")

    await client.post("/api/v1/auth/logout")

    # Access token still works when sent explicitly in Authorization header until TTL
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {old_access}"},
    )
    assert r.status_code == 200