"""
ChatSessionService — end-user session lifecycle.

Sessions are scoped to a specific chatbot (via workspace_slug + chatbot_id).
Authentication uses a short-lived session token, NOT the workspace JWT.

Session token design:
  - 64-char random URL-safe string
  - Stored as plaintext in chat_sessions (needed for lookup on every WS message)
  - Expires after SESSION_TTL_HOURS (default 4h)
  - Rate-limited per end_user_id or remote IP via Redis
"""

from __future__ import annotations

import uuid
from datetime import timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import ChatSession, ChatbotCollection, WorkspaceMember
from app.data.repositories.chat_repo import (
    ChatMessageRepository,
    ChatSessionRepository,
    UsageLogRepository,
)
from app.data.repositories.chatbot_repo import ChatbotRepository
from app.data.repositories.workspace_repo import WorkspaceRepository
from app.schemas.chat import (
    CreateSessionRequest,
    MessageListOut,
    MessageOut,
    SessionEndedOut,
    SessionOut,
)
from app.utils.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.utils.security import generate_secure_token, token_expiry

SESSION_TTL_HOURS = 4


class ChatSessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db        = db
        self.ses_repo  = ChatSessionRepository(db)
        self.msg_repo  = ChatMessageRepository(db)
        self.bot_repo  = ChatbotRepository(db)
        self.ws_repo   = WorkspaceRepository(db)

    # ── Create session ────────────────────────────────────────────────────────

    async def create_session(
        self,
        workspace_slug: str,
        chatbot_id: uuid.UUID,
        data: CreateSessionRequest,
    ) -> SessionOut:
        workspace = await self.ws_repo.get_by_slug(workspace_slug)
        if not workspace:
            raise NotFoundError("Workspace")

        chatbot = await self.bot_repo.get_by_id_in_workspace(
            chatbot_id, workspace.id
        )
        if not chatbot:
            raise NotFoundError("Chatbot")
        if not chatbot.is_active or chatbot.deployment_status != "published":
            raise BadRequestError("This chatbot is not currently available.")

        token = generate_secure_token(64)
        expires = token_expiry(hours=SESSION_TTL_HOURS)

        session = await self.ses_repo.create(
            workspace_id=workspace.id,
            chatbot_id=chatbot_id,
            end_user_id=data.end_user_id,
            session_token=token,
            session_token_expires_at=expires,
            expires_at=expires,
            metadata_=data.metadata,
        )

        session_out = SessionOut.model_validate(session)
        session_out.welcome_message = chatbot.welcome_message
        session_out.brand_color = chatbot.brand_color
        session_out.chatbot_name = chatbot.name
        return session_out


    async def create_playground_session(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        data: CreateSessionRequest,
        member: WorkspaceMember,
    ) -> SessionOut:
        chatbot = await self.bot_repo.get_by_id_in_workspace(
            chatbot_id, workspace_id
        )
        if not chatbot:
            raise NotFoundError("Chatbot")
        
        # Playground bypasses the 'published' and 'is_active' check

        token = generate_secure_token(64)
        expires = token_expiry(hours=SESSION_TTL_HOURS)

        # Set end_user_id to track playground usage
        end_user_id = f"playground-{member.user_id}"

        session = await self.ses_repo.create(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            end_user_id=end_user_id,
            session_token=token,
            session_token_expires_at=expires,
            expires_at=expires,
            metadata_=data.metadata,
        )

        session_out = SessionOut.model_validate(session)
        session_out.welcome_message = chatbot.welcome_message
        session_out.brand_color = chatbot.brand_color
        session_out.chatbot_name = chatbot.name
        return session_out

        
    # ── Validate session token ────────────────────────────────────────────────

    async def validate_session_token(self, token: str) -> ChatSession:
        """
        Validate a session token.
        Called on every WebSocket message and REST request from end-users.
        Raises 401 / 403 on invalid, expired, or ended sessions.
        """
        from app.utils.exceptions import UnauthorizedError
        session = await self.ses_repo.get_by_token(token)
        if not session:
            raise UnauthorizedError("Invalid session token.")
        if session.session_status != "active":
            raise ForbiddenError("This session has ended.")
        now = _utcnow()
        if session.expires_at.replace(tzinfo=timezone.utc) < now:
            await self.ses_repo.update(session, session_status="expired")
            raise ForbiddenError("Session has expired. Please start a new chat.")
        return session

    # ── Get message history ───────────────────────────────────────────────────

    async def get_messages(
        self,
        workspace_slug: str,
        chatbot_id: uuid.UUID,
        session_id: uuid.UUID,
        session_token: str,
        limit: int = 50,
        offset: int = 0,
    ) -> MessageListOut:
        session = await self.validate_session_token(session_token)
        if session.id != session_id:
            raise ForbiddenError("Session token does not match session ID.")

        workspace = await self.ws_repo.get_by_slug(workspace_slug)
        if not workspace:
            raise NotFoundError("Workspace")

        messages = await self.msg_repo.list_for_session(
            session_id=session_id,
            workspace_id=workspace.id,
            chatbot_id=chatbot_id,
            limit=limit,
            offset=offset,
        )
        return MessageListOut(
            messages=[MessageOut.model_validate(m) for m in messages],
            total=len(messages),
            limit=limit,
            offset=offset,
        )

    async def get_playground_messages(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        session_id: uuid.UUID,
        session_token: str,
        limit: int = 50,
        offset: int = 0,
    ) -> MessageListOut:
        session = await self.validate_session_token(session_token)
        if session.id != session_id or session.workspace_id != workspace_id or session.chatbot_id != chatbot_id:
            raise ForbiddenError("Session token does not match requested identifiers.")

        messages = await self.msg_repo.list_for_session(
            session_id=session_id,
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            limit=limit,
            offset=offset,
        )
        return MessageListOut(
            messages=[MessageOut.model_validate(m) for m in messages],
            total=len(messages),
            limit=limit,
            offset=offset,
        )

    # ── End session ───────────────────────────────────────────────────────────

    async def end_session(
        self,
        workspace_slug: str,
        chatbot_id: uuid.UUID,
        session_id: uuid.UUID,
        session_token: str,
        summarize: bool = True,
    ) -> SessionEndedOut:
        session = await self.validate_session_token(session_token)
        if session.id != session_id:
            raise ForbiddenError("Session token does not match session ID.")

        summary: str | None = None
        if summarize and session.message_count >= 4:
            # Trigger async summarization — chatbot-rag handles this
            # For now we record it as a pending action (summary updated by callback)
            summary = None

        ended = await self.ses_repo.end_session(session, summary)

        return SessionEndedOut(
            session_id=ended.id,
            session_status=ended.session_status,
            duration_seconds=ended.duration_seconds,
            message_count=ended.message_count,
            total_tokens=ended.total_tokens,
            session_summary=ended.session_summary,
        )

    async def end_playground_session(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        session_id: uuid.UUID,
        session_token: str,
        summarize: bool = True,
    ) -> SessionEndedOut:
        session = await self.validate_session_token(session_token)
        if session.id != session_id or session.workspace_id != workspace_id or session.chatbot_id != chatbot_id:
            raise ForbiddenError("Session token does not match requested identifiers.")

        summary: str | None = None
        if summarize and session.message_count >= 4:
            summary = None

        ended = await self.ses_repo.end_session(session, summary)

        return SessionEndedOut(
            session_id=ended.id,
            session_status=ended.session_status,
            duration_seconds=ended.duration_seconds,
            message_count=ended.message_count,
            total_tokens=ended.total_tokens,
            session_summary=ended.session_summary,
        )


def _utcnow():
    from datetime import datetime
    return datetime.now(timezone.utc)