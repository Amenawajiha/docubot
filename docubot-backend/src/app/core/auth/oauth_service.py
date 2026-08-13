"""
OAuth service — Google and GitHub social login.

Flow:
  1. Frontend calls GET /auth/google  → receives {url: "..."}
  2. Frontend redirects the browser to that URL
  3. Provider redirects back to /auth/google/callback?code=...
  4. Backend exchanges code for user profile, finds-or-creates User,
     issues its own JWT access + refresh tokens
  5. Backend redirects browser to frontend with tokens in query string
     (localStorage strategy) — frontend reads them and stores locally

Account linking:
  - If an OAuth email matches an existing email/password account, the
    OAuth provider is linked to that account automatically.
  - If a user registers with Google then tries GitHub with the same
    email, GitHub will be linked to the same account too.
"""

from __future__ import annotations

import urllib.parse

import httpx
from app.config import settings
from app.core.auth.jwt_handler import create_access_token, create_refresh_token
from google.oauth2 import id_token
from google.auth.transport import requests
from app.data.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse, UserOut
from app.utils.exceptions import BadRequestError
from sqlalchemy.ext.asyncio import AsyncSession


class OAuthService:
    def __init__(self, session: AsyncSession | None) -> None:
        self.session = session
        # user_repo is only needed in callback handlers, not URL builders.
        # Passing session=None is valid for get_google_auth_url / get_github_auth_url.
        self.user_repo: UserRepository | None = (
            UserRepository(session) if session is not None else None
        )

    def _require_repo(self) -> UserRepository:
        """Call inside DB-dependent methods to assert repo is available."""
        if self.user_repo is None:
            raise RuntimeError(
                "OAuthService was constructed without a DB session. "
                "This method requires one."
            )
        return self.user_repo

    # ── Authorization URL builders ────────────────────────────────────────────

    def get_github_auth_url(self, state: str) -> str:
        """Return the GitHub OAuth authorization URL to redirect the user to."""
        params = {
            "client_id": settings.github_client_id,
            "redirect_uri": settings.github_redirect_uri,
            "scope": "user:email",
            "state": state,
        }
        return "https://github.com/login/oauth/authorize?" + urllib.parse.urlencode(params)

    # ── Callback handlers ─────────────────────────────────────────────────────

    async def verify_google_token(self, token: str) -> TokenResponse:
        """
        Verify the Google ID token (credential) obtained from the frontend via 
        Google Identity Services (GIS).
        
        NOTE: The old Web Server flow (code exchange) was removed in favor of this GIS approach.
        The old logic worked as follows:
          1. GET /auth/google redirected to Google with client_id, response_type=code, and scope.
          2. Provider redirected back to /auth/google/callback?code=...
          3. Backend exchanged code for access_token via oauth2.googleapis.com/token.
          4. Backend fetched user profile via www.googleapis.com/oauth2/v3/userinfo.
          5. Backend issued JWTs and sent a 302 redirect back to the UI.
        We now use the implicit flow on the frontend, and verify the token here directly.
        """
        try:
            # Automatically fetches and caches Google's public keys to verify the signature
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                settings.google_client_id
            )
        except ValueError:
            raise BadRequestError("Invalid Google token.")

        return await self._find_or_create_user(
            provider="google",
            provider_id=idinfo["sub"],
            email=idinfo.get("email"),
            full_name=idinfo.get("name"),
            avatar_url=idinfo.get("picture"),
            email_verified=idinfo.get("email_verified", False),
        )

    async def handle_github_callback(self, code: str) -> TokenResponse:
        """Exchange GitHub auth code for tokens and return our own JWT pair."""
        async with httpx.AsyncClient() as client:
            # Exchange code for access token
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "code": code,
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "redirect_uri": settings.github_redirect_uri,
                },
            )
            if token_resp.status_code != 200:
                raise BadRequestError("Failed to exchange GitHub authorization code.")

            token_data = token_resp.json()
            if "error" in token_data:
                raise BadRequestError(
                    f"GitHub OAuth error: {token_data.get('error_description', token_data['error'])}"
                )

            gh_access_token = token_data.get("access_token")
            auth_headers = {
                "Authorization": f"Bearer {gh_access_token}",
                "Accept": "application/vnd.github+json",
            }

            # Fetch user profile
            profile_resp = await client.get(
                "https://api.github.com/user", headers=auth_headers
            )
            if profile_resp.status_code != 200:
                raise BadRequestError("Failed to fetch GitHub user profile.")

            profile = profile_resp.json()

            # GitHub doesn't always include email in the profile — fetch separately
            email: str | None = profile.get("email")
            if not email:
                emails_resp = await client.get(
                    "https://api.github.com/user/emails", headers=auth_headers
                )
                if emails_resp.status_code == 200:
                    emails = emails_resp.json()
                    # Pick the primary verified email
                    email = next(
                        (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                        # Fall back to any verified email
                        next(
                            (e["email"] for e in emails if e.get("verified")),
                            None,
                        ),
                    )

        if not email:
            raise BadRequestError(
                "Your GitHub account has no verified email address. "
                "Please add and verify one in GitHub settings, then try again."
            )

        return await self._find_or_create_user(
            provider="github",
            provider_id=str(profile["id"]),
            email=email,
            full_name=profile.get("name"),
            avatar_url=profile.get("avatar_url"),
            email_verified=True,  # GitHub emails in the API are verified
        )

    # ── Frontend redirect URL builder ─────────────────────────────────────────

    @staticmethod
    def build_frontend_redirect(token_response: TokenResponse) -> str:
        """
        Build the URL the backend redirects to after OAuth success.

        Tokens are passed as query parameters so the frontend JS can
        read them and store in localStorage.

        e.g. http://localhost:3000/auth/callback
               ?access_token=eyJ...
               &refresh_token=eyJ...
               &expires_in=3600
        """
        params = {
            "access_token": token_response.access_token,
            "refresh_token": token_response.refresh_token,
            "expires_in": str(token_response.expires_in),
        }
        return f"{settings.frontend_url}/auth/verify-success?" + urllib.parse.urlencode(params)

    @staticmethod
    def build_frontend_error_redirect(message: str) -> str:
        """Build a redirect URL for OAuth errors so the frontend can show them."""
        params = {"error": message}
        return f"{settings.frontend_url}/auth/verify-success?" + urllib.parse.urlencode(params)

    # ── Core find-or-create logic ─────────────────────────────────────────────

    async def _find_or_create_user(
        self,
        *,
        provider: str,
        provider_id: str,
        email: str | None,
        full_name: str | None,
        avatar_url: str | None,
        email_verified: bool,
    ) -> TokenResponse:
        repo = self._require_repo()
        # 1. Look up by provider + provider_id (returning user via same provider)
        user = await repo.get_by_oauth(provider, provider_id)

        if not user and email:
            # 2. Look up by email — link OAuth to existing email/password account
            user = await repo.get_by_email(email)
            if user:
                await repo.update(
                    user,
                    oauth_provider=provider,
                    oauth_provider_id=provider_id,
                    avatar_url=avatar_url or user.avatar_url,
                    # Mark email verified since the provider confirmed it
                    email_verified=True,
                )

        if not user:
            # 3. Brand new user — create account
            if not email:
                raise BadRequestError(
                    "Could not retrieve a verified email from the OAuth provider."
                )
            user = await repo.create(
                email=email.lower(),
                password_hash=None,         # no password for OAuth-only users
                full_name=full_name,
                email_verified=email_verified,
                oauth_provider=provider,
                oauth_provider_id=provider_id,
                avatar_url=avatar_url,
            )

        await repo.touch_last_login(user)

        # Issue our own JWT tokens
        access_token = create_access_token(user.id)
        refresh_token, _ = create_refresh_token(user.id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserOut.model_validate(user),
        )