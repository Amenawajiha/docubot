"""
Tests: GET /api/v1/auth/google
       GET /api/v1/auth/github
       OAuthService._find_or_create_user() logic (unit tests)

OAuth callback endpoints are NOT integration-tested here because they require
a real OAuth code from Google/GitHub. The core find-or-create logic is tested
directly against the DB instead.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import get_verification_token, full_login


# ── URL endpoints ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_google_auth_url_returned(client: AsyncClient):
    """GET /auth/google returns a valid Google OAuth URL."""
    r = await client.get("/api/v1/auth/google")
    assert r.status_code == 200
    body = r.json()
    assert "url" in body
    assert "accounts.google.com" in body["url"]
    assert "response_type=code" in body["url"]
    assert "scope=openid" in body["url"]


@pytest.mark.asyncio
async def test_github_auth_url_returned(client: AsyncClient):
    """GET /auth/github returns a valid GitHub OAuth URL."""
    r = await client.get("/api/v1/auth/github")
    assert r.status_code == 200
    body = r.json()
    assert "url" in body
    assert "github.com/login/oauth/authorize" in body["url"]
    assert "user%3Aemail" in body["url"] or "user:email" in body["url"]


@pytest.mark.asyncio
async def test_google_url_contains_redirect_uri(client: AsyncClient):
    """Google URL contains the configured redirect URI."""
    r = await client.get("/api/v1/auth/google")
    assert "redirect_uri" in r.json()["url"]
    assert "google%2Fcallback" in r.json()["url"] or "google/callback" in r.json()["url"]


@pytest.mark.asyncio
async def test_github_url_contains_redirect_uri(client: AsyncClient):
    """GitHub URL contains the configured redirect URI."""
    r = await client.get("/api/v1/auth/github")
    assert "redirect_uri" in r.json()["url"]
    assert "github%2Fcallback" in r.json()["url"] or "github/callback" in r.json()["url"]


# ── OAuthService._find_or_create_user() unit tests ───────────────────────────

@pytest.mark.asyncio
async def test_oauth_creates_new_user(db_session: AsyncSession):
    """Brand new OAuth user is created with no password_hash."""
    from app.core.auth.oauth_service import OAuthService

    svc = OAuthService(db_session)
    tokens = await svc._find_or_create_user(
        provider="google",
        provider_id="google-uid-001",
        email="newoauth@gmail.com",
        full_name="New OAuth",
        avatar_url="https://lh3.googleusercontent.com/photo.jpg",
        email_verified=True,
    )
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.user.email == "newoauth@gmail.com"
    assert tokens.user.oauth_provider == "google"
    assert tokens.user.email_verified is True
    assert tokens.user.avatar_url == "https://lh3.googleusercontent.com/photo.jpg"


@pytest.mark.asyncio
async def test_oauth_returning_user_recognised(db_session: AsyncSession):
    """Same provider_id on second call finds the existing user."""
    from app.core.auth.oauth_service import OAuthService

    svc = OAuthService(db_session)
    first = await svc._find_or_create_user(
        provider="google", provider_id="google-uid-002",
        email="returning@gmail.com", full_name="Return", avatar_url=None,
        email_verified=True,
    )
    second = await svc._find_or_create_user(
        provider="google", provider_id="google-uid-002",
        email="returning@gmail.com", full_name="Return", avatar_url=None,
        email_verified=True,
    )
    # Same user ID
    assert first.user.id == second.user.id


@pytest.mark.asyncio
async def test_oauth_links_to_existing_email_password_account(
    client: AsyncClient, db_session: AsyncSession
):
    """
    OAuth login with an email that matches an existing email/password account
    links the OAuth provider to that account instead of creating a new one.
    """
    from app.core.auth.oauth_service import OAuthService
    from sqlalchemy import select
    from app.data.models import User

    # Create email/password account first
    await full_login(client, db_session, "link@gmail.com")

    # Now OAuth with same email
    svc = OAuthService(db_session)
    tokens = await svc._find_or_create_user(
        provider="github",
        provider_id="gh-link-001",
        email="link@gmail.com",
        full_name="Link User",
        avatar_url=None,
        email_verified=True,
    )

    # Must be the SAME user, not a new one
    assert tokens.user.email == "link@gmail.com"
    assert tokens.user.oauth_provider == "github"
        
    # Verify the DB actually saved the provider ID
    result = await db_session.execute(select(User).where(User.id == tokens.user.id))
    db_user = result.scalar_one()
    assert db_user.oauth_provider_id == "gh-link-001"

    # Only one user in DB with this email
    result = await db_session.execute(
        select(User).where(User.email == "link@gmail.com")
    )
    users = result.scalars().all()
    assert len(users) == 1


@pytest.mark.asyncio
async def test_oauth_email_verified_after_linking(
    client: AsyncClient, db_session: AsyncSession
):
    """
    If an unverified email/password account is linked via OAuth,
    the account becomes email_verified=True (provider confirmed the email).
    """
    from app.core.auth.oauth_service import OAuthService
    from sqlalchemy import select
    from app.data.models import User

    # Register but do NOT verify email
    await client.post("/api/v1/auth/register", json={
        "email": "unveroauth@gmail.com", "password": "Password1"
    })

    # OAuth login with same email
    svc = OAuthService(db_session)
    await svc._find_or_create_user(
        provider="google",
        provider_id="g-unver-001",
        email="unveroauth@gmail.com",
        full_name=None,
        avatar_url=None,
        email_verified=True,
    )

    result = await db_session.execute(
        select(User.email_verified).where(User.email == "unveroauth@gmail.com")
    )
    assert result.scalar_one() is True


@pytest.mark.asyncio
async def test_oauth_no_email_raises_bad_request(db_session: AsyncSession):
    """Creating a new OAuth user without an email raises BadRequestError."""
    from app.core.auth.oauth_service import OAuthService
    from app.utils.exceptions import BadRequestError

    svc = OAuthService(db_session)
    with pytest.raises(BadRequestError):
        await svc._find_or_create_user(
            provider="github",
            provider_id="gh-no-email",
            email=None,
            full_name=None,
            avatar_url=None,
            email_verified=False,
        )


@pytest.mark.asyncio
async def test_oauth_url_builder_no_session_needed():
    """OAuthService URL builders work with session=None (no DB call)."""
    from app.core.auth.oauth_service import OAuthService

    svc = OAuthService(None)
    # Must not raise
    google_url = svc.get_google_auth_url(state="some_test_state")
    github_url = svc.get_github_auth_url(state="some_test_state")
    assert "google.com" in google_url
    assert "github" in github_url


@pytest.mark.asyncio
async def test_frontend_redirect_url_structure():
    """build_frontend_redirect puts tokens in the query string correctly."""
    from app.core.auth.oauth_service import OAuthService
    from app.schemas.auth import TokenResponse, UserOut
    from datetime import datetime
    import uuid

    fake_response = TokenResponse(
        access_token="acc123",
        refresh_token="ref456",
        expires_in=3600,
        user=UserOut(
            id=uuid.uuid4(),
            email="test@example.com",
            full_name=None,
            avatar_url=None,
            email_verified=True,
            is_active=True,
            oauth_provider="google",
            created_at=datetime.utcnow(),
            last_login_at=None,
        )
    )
    url = OAuthService.build_frontend_redirect(fake_response)
    assert "access_token=acc123" in url
    assert "refresh_token=ref456" in url
    assert "expires_in=3600" in url
    assert "localhost:3000" in url
    assert "/auth/verify-success" in url


@pytest.mark.asyncio
async def test_frontend_error_redirect_url_structure():
    """build_frontend_error_redirect includes the error message."""
    from app.core.auth.oauth_service import OAuthService

    url = OAuthService.build_frontend_error_redirect("Something went wrong")
    assert "error=" in url
    assert "/auth/verify-success" in url