"""
Central email sender.

In development (MAIL_SUPPRESS_SEND=true) every email is printed to stdout
instead of actually sending, so you can test the full auth flow without an
SMTP server or valid credentials.

In production set MAIL_SUPPRESS_SEND=false and fill in the MAIL_* env vars.
Supports any SMTP provider (Gmail, SendGrid SMTP relay, Resend SMTP, etc.)

Design note
-----------
ConnectionConfig is constructed lazily (on first send) rather than at module
import time. This means the app starts cleanly even when MAIL_USERNAME /
MAIL_PASSWORD are empty — which is the normal dev setup when suppress is on.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.config import settings


@lru_cache
def _get_mailer() -> FastMail:
    """
    Build and cache the FastMail instance.

    Called only when an email actually needs to be sent (i.e. suppress=False).
    This defers validation of SMTP credentials until runtime, so an empty
    MAIL_USERNAME in dev never raises an error at startup.
    """
    config = ConnectionConfig(
        MAIL_USERNAME=settings.mail_username,
        MAIL_PASSWORD=settings.mail_password,
        MAIL_FROM=settings.mail_from,
        MAIL_FROM_NAME=settings.mail_from_name,
        MAIL_PORT=settings.mail_port,
        MAIL_SERVER=settings.mail_server,
        MAIL_STARTTLS=settings.mail_starttls,
        MAIL_SSL_TLS=settings.mail_ssl_tls,
        MAIL_DEBUG=settings.debug,
        SUPPRESS_SEND=False,  # we gate this ourselves — never suppress inside FastMail
        USE_CREDENTIALS=bool(settings.mail_username and settings.mail_password),
        TEMPLATE_FOLDER=Path(__file__).parent / "templates",
    )
    return FastMail(config)


async def _send(
    *,
    to: str,
    subject: str,
    template_name: str,
    context: dict[str, Any],
) -> None:
    """Internal: actually dispatch one templated email via SMTP."""
    message = MessageSchema(
        subject=subject,
        recipients=[to],
        template_body=context,
        subtype=MessageType.html,
    )
    await _get_mailer().send_message(message, template_name=template_name)


# ── Public helpers ─────────────────────────────────────────────────────────────

async def send_verification_email(email: str, token: str, full_name: str | None) -> None:
    link = f"{settings.backend_url}/api/v1/auth/verify-email?token={token}"
    if settings.mail_suppress_send:
        print(f"\n[DEV EMAIL] Verification link for {email}:\n  {link}\n")  # noqa: T201
        return
    await _send(
        to=email,
        subject="Verify your DocuBot email address",
        template_name="verify_email.html",
        context={"full_name": full_name or "there", "link": link},
    )


async def send_password_reset_email(email: str, token: str, full_name: str | None) -> None:
    link = f"{settings.frontend_url}/reset-password?token={token}"
    if settings.mail_suppress_send:
        print(f"\n[DEV EMAIL] Password reset link for {email}:\n  {link}\n")  # noqa: T201
        return
    await _send(
        to=email,
        subject="Reset your DocuBot password",
        template_name="reset_password.html",
        context={"full_name": full_name or "there", "link": link},
    )


async def send_workspace_invitation_email(
    email: str,
    token: str,
    workspace_name: str,
    invited_by_name: str,
) -> None:
    link = f"{settings.frontend_url}/accept-invite?token={token}"
    if settings.mail_suppress_send:
        print(  # noqa: T201
            f"\n[DEV EMAIL] Workspace invitation for {email} "
            f"to '{workspace_name}':\n  {link}\n"
        )
        return
    await _send(
        to=email,
        subject=f"You've been invited to {workspace_name} on DocuBot",
        template_name="workspace_invite.html",
        context={
            "workspace_name": workspace_name,
            "invited_by_name": invited_by_name,
            "link": link,
        },
    )