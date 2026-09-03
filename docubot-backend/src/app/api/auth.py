
from fastapi import APIRouter, Body, Depends, Request, Response, status, Query
from fastapi.responses import RedirectResponse

from app.api.dependencies import CurrentUser, DbSession
from app.core.auth.service import AuthService
from app.core.auth.oauth_service import OAuthService
from app.data.repositories.user_repo import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    OAuthUrlResponse,
    RefreshTokenRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
    UserUpdate,
    VerifyEmailRequest,
    GoogleVerifyRequest,
)
from app.utils.exceptions import BadRequestError, ConflictError
from app.utils.security import generate_secure_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


def _svc(session: DbSession) -> AuthService:
    return AuthService(session)

def _oauth_svc(session: DbSession) -> OAuthService:
    return OAuthService(session)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user account",
)
async def register(
    data: RegisterRequest,
    session: DbSession,
) -> UserOut:
    return await _svc(session).register(data)


@router.api_route(
    "/verify-email",
    methods=["GET", "POST"],
    summary="Verify email address with token from email",
    include_in_schema=False,  # Hide from Swagger since it redirects
)
async def verify_email(
    session: DbSession,
    token: str | None = Query(None, description="Verification token (from email link)"),
) -> RedirectResponse:
    if not token:
        frontend_error_url = f"{settings.frontend_url}/auth/verify-error?reason=no_token"
        return RedirectResponse(url=frontend_error_url, status_code=status.HTTP_302_FOUND)
    
    try:
        token_response = await _svc(session).verify_email(VerifyEmailRequest(token=token))
        callback_url = f"{settings.frontend_url}/auth/verify-success"
        redirect_response = RedirectResponse(url=callback_url, status_code=status.HTTP_302_FOUND)
        redirect_response.set_cookie(
            key="access_token",
            value=token_response.access_token,
            httponly=True,
            secure=settings.is_production,
            samesite="lax",
            max_age=settings.access_token_expire_minutes * 60
        )
        redirect_response.set_cookie(
            key="refresh_token",
            value=token_response.refresh_token,
            httponly=True,
            secure=settings.is_production,
            samesite="lax",
            max_age=settings.refresh_token_expire_days * 86400
        )
        return redirect_response
    except BadRequestError as e:
        error_url = f"{settings.frontend_url}/auth/verify-error?reason={str(e)}"
        return RedirectResponse(url=error_url, status_code=status.HTTP_302_FOUND)

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and receive access + refresh tokens",
)
async def login(
    response: Response,
    data: LoginRequest,
    session: DbSession,
) -> TokenResponse:
    token_response = await _svc(session).login(data)
    response.set_cookie(
        key="access_token",
        value=token_response.access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=token_response.refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )
    token_response.access_token = ""
    token_response.refresh_token = ""
    return token_response


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Rotate refresh token and get new access token",
)
async def refresh(
    request: Request,
    response: Response,
    session: DbSession,
    data: RefreshTokenRequest | None = Body(default=None),
) -> TokenResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token and data:
        refresh_token = data.refresh_token

    if not refresh_token:
        from app.utils.exceptions import UnauthorizedError
        raise UnauthorizedError("Refresh token is missing.")

    token_response = await _svc(session).refresh(RefreshTokenRequest(refresh_token=refresh_token))
    response.set_cookie(
        key="access_token",
        value=token_response.access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=token_response.refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )
    token_response.access_token = ""
    token_response.refresh_token = ""
    return token_response


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Invalidate refresh token",
)
async def logout(
    request: Request,
    response: Response,
    session: DbSession,
    data: RefreshTokenRequest | None = Body(default=None),
) -> MessageResponse:
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token and data:
        refresh_token = data.refresh_token

    if refresh_token:
        await _svc(session).logout(refresh_token)

    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return MessageResponse(message="Logged out successfully.")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset email",
)
async def forgot_password(
    data: ForgotPasswordRequest,
    session: DbSession,
) -> MessageResponse:
    await _svc(session).forgot_password(data)
    return MessageResponse(
        message="If an account exists with that email, a reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using token from email",
)
async def reset_password(
    data: ResetPasswordRequest,
    session: DbSession,
) -> MessageResponse:
    await _svc(session).reset_password(data)
    return MessageResponse(message="Password reset successfully.")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change password for the authenticated user",
)
async def change_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> MessageResponse:
    await _svc(session).change_password(current_user, data)
    return MessageResponse(message="Password changed successfully.")


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get authenticated user profile",
)
async def me(current_user: CurrentUser) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update authenticated user profile",
)
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> UserOut:
    user_repo = UserRepository(session)
    updates = {}
    if data.full_name is not None:
        updates["full_name"] = data.full_name
    if data.email is not None:
        new_email = data.email.lower()
        if new_email != current_user.email:
            if await user_repo.email_exists(new_email):
                raise ConflictError("An account with this email already exists.")
            updates["email"] = new_email
    
    if updates:
        current_user = await user_repo.update(current_user, **updates)
    return UserOut.model_validate(current_user)


# ── Google OAuth ──────────────────────────────────────────────────────────────


@router.post(
    "/google/verify",
    response_model=TokenResponse,
    summary="Verify Google ID Token from client",
)
async def verify_google(
    request: GoogleVerifyRequest,
    response: Response,
    session: DbSession,
) -> TokenResponse:
    svc = _oauth_svc(session)
    token_response = await svc.verify_google_token(request.credential)
    
    response.set_cookie(
        key="access_token",
        value=token_response.access_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=token_response.refresh_token,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
    )
    
    token_response.access_token = ""
    token_response.refresh_token = ""
    return token_response


# ── GitHub OAuth ──────────────────────────────────────────────────────────────


@router.get(
    "/github",
    response_model=OAuthUrlResponse,
    summary="Get GitHub OAuth authorization URL",
)
async def get_github_auth_url(response: Response) -> OAuthUrlResponse:
    state = generate_secure_token(32)
    response.set_cookie(
        key="oauth_state",
        value=state,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        max_age=600
    )
    url = OAuthService(None).get_github_auth_url(state)
    return OAuthUrlResponse(url=url)


@router.get(
    "/github/callback",
    summary="GitHub OAuth callback handler",
    include_in_schema=False,
)
async def github_callback(
    code: str,
    state: str,
    request: Request,
    session: DbSession,
) -> RedirectResponse:
    cookie_state = request.cookies.get("oauth_state")

    if not cookie_state or cookie_state != state:
        redirect_url = f"{settings.frontend_url}/auth/verify-error?reason=csrf_detected"
        redirect_response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        redirect_response.delete_cookie("oauth_state")
        return redirect_response

    svc = _oauth_svc(session)
    try: 
        token_response = await svc.handle_github_callback(code)
        callback_url = f"{settings.frontend_url}/auth/verify-success"
        redirect_response = RedirectResponse(url=callback_url, status_code=status.HTTP_302_FOUND)
        redirect_response.delete_cookie("oauth_state")
        redirect_response.set_cookie(
            key="access_token",
            value=token_response.access_token,
            httponly=True,
            secure=settings.is_production,
            samesite="lax",
            max_age=settings.access_token_expire_minutes * 60
        )
        redirect_response.set_cookie(
            key="refresh_token",
            value=token_response.refresh_token,
            httponly=True,
            secure=settings.is_production,
            samesite="lax",
            max_age=settings.refresh_token_expire_days * 86400
        )
        return redirect_response
    except Exception as exc:
        redirect_url = OAuthService.build_frontend_error_redirect(str(exc))
        redirect_response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
        redirect_response.delete_cookie("oauth_state")
        return redirect_response