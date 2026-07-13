"""
ChatbotService — chatbot lifecycle: create, list, get, delete, deploy, pause.

Configuration reads/writes (LLM tuning, RAG settings, widget config) are
handled by ChatbotConfigManager (core/chatbot/config_manager.py).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import Chatbot, User
from app.data.repositories.chatbot_repo import ChatbotRepository
from app.data.repositories.workspace_repo import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from app.schemas.chatbot import (
    ChatbotCreate,
    ChatbotDeployResponse,
    ChatbotListOut,
    ChatbotOut,
)
from app.utils.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.utils.security import encrypt_api_key, hash_password

# Owner is identified by workspace.owner_id — not a rank entry.
_ROLE_RANK: dict[str, int] = {"viewer": 0, "editor": 1, "admin": 2}


class ChatbotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bot_repo = ChatbotRepository(session)
        self.ws_repo = WorkspaceRepository(session)
        self.mem_repo = WorkspaceMemberRepository(session)

    # ── Create ────────────────────────────────────────────────────────────────

    async def create(
        self, workspace_id: uuid.UUID, data: ChatbotCreate, actor: User
    ) -> ChatbotOut:
        ws = await self._require_workspace(workspace_id)
        await self._require_role(workspace_id, actor.id, "editor")

        # Enforce workspace chatbot limit
        current_count = await self.bot_repo.count_active_for_workspace(workspace_id)
        if current_count >= ws.chatbot_limit:
            raise BadRequestError(
                f"Workspace chatbot limit reached ({ws.chatbot_limit}). "
                "Upgrade your plan or archive an existing chatbot."
            )

        encrypted_key: str | None = (
            encrypt_api_key(data.custom_api_key) if data.custom_api_key else None
        )
        passcode_hash: str | None = (
            hash_password(data.passcode) if data.passcode else None
        )

        chatbot = await self.bot_repo.create(
            workspace_id=workspace_id,
            name=data.name,
            avatar_emoji=data.avatar_emoji,
            brand_color=data.brand_color,
            llm_provider=data.llm_provider,
            llm_model=data.llm_model,
            custom_api_key_encrypted=encrypted_key,
            temperature=str(data.temperature),
            max_tokens=data.max_tokens,
            top_p=str(data.top_p),
            tone_preset=data.tone_preset,
            custom_system_prompt=data.custom_system_prompt,
            default_language=data.default_language,
            fallback_language=data.fallback_language,
            widget_style=data.widget_style,
            welcome_message=data.welcome_message,
            input_placeholder=data.input_placeholder,
            show_citations=data.show_citations,
            memory_mode=data.memory_mode,
            context_depth=data.context_depth,
            retrieval_top_k=data.retrieval_top_k,
            confidence_threshold=str(data.confidence_threshold),
            auth_mode=data.auth_mode,
            passcode_hash=passcode_hash,
        )

        return _to_out(chatbot)

    # ── List / Get ────────────────────────────────────────────────────────────

    async def list_for_workspace(
        self,
        workspace_id: uuid.UUID,
        actor: User,
        include_archived: bool = False,
    ) -> list[ChatbotListOut]:
        await self._require_member(workspace_id, actor.id)
        chatbots = await self.bot_repo.list_for_workspace(
            workspace_id, include_archived=include_archived
        )
        return [_to_list_out(c) for c in chatbots]

    async def get(
        self, workspace_id: uuid.UUID, chatbot_id: uuid.UUID, actor: User
    ) -> ChatbotOut:
        await self._require_member(workspace_id, actor.id)
        chatbot = await self._require_chatbot(workspace_id, chatbot_id)
        return _to_out(chatbot)

    # ── Delete ────────────────────────────────────────────────────────────────

    async def delete(
        self, workspace_id: uuid.UUID, chatbot_id: uuid.UUID, actor: User
    ) -> None:
        await self._require_role(workspace_id, actor.id, "admin")
        chatbot = await self._require_chatbot(workspace_id, chatbot_id)
        await self.bot_repo.soft_delete(chatbot)

    # ── Deploy / Pause ────────────────────────────────────────────────────────

    async def deploy(
        self, workspace_id: uuid.UUID, chatbot_id: uuid.UUID, actor: User
    ) -> ChatbotDeployResponse:
        await self._require_role(workspace_id, actor.id, "editor")
        chatbot = await self._require_chatbot(workspace_id, chatbot_id)

        chatbot = await self.bot_repo.update(
            chatbot,
            is_active=True,
            deployment_status="published",
            last_deployed_at=datetime.now(timezone.utc),
        )

        return ChatbotDeployResponse(
            id=chatbot.id,
            deployment_status=chatbot.deployment_status,
            is_active=chatbot.is_active,
            last_deployed_at=chatbot.last_deployed_at,
            embed_snippet=_build_embed_snippet(chatbot.id),
        )

    async def pause(
        self, workspace_id: uuid.UUID, chatbot_id: uuid.UUID, actor: User
    ) -> ChatbotOut:
        await self._require_role(workspace_id, actor.id, "editor")
        chatbot = await self._require_chatbot(workspace_id, chatbot_id)
        chatbot = await self.bot_repo.update(
            chatbot, is_active=False, deployment_status="paused"
        )
        return _to_out(chatbot)

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _require_workspace(self, workspace_id: uuid.UUID):
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        if not ws:
            raise NotFoundError("Workspace")
        return ws

    async def _require_chatbot(
        self, workspace_id: uuid.UUID, chatbot_id: uuid.UUID
    ) -> Chatbot:
        bot = await self.bot_repo.get_by_id_in_workspace(chatbot_id, workspace_id)
        if not bot:
            raise NotFoundError("Chatbot")
        return bot

    async def _require_member(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> None:
        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")

    async def _require_role(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID, min_role: str
    ) -> None:
        """Assert user has at least `min_role`. Owner always passes."""
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        if ws and ws.owner_id == user_id:
            return  # owner outranks every role

        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")

        if _ROLE_RANK.get(member.role, -1) < _ROLE_RANK.get(min_role, 99):
            raise ForbiddenError(
                f"This action requires at least the '{min_role}' role."
            )


# ── Serialisers ───────────────────────────────────────────────────────────────

def _to_out(c: Chatbot) -> ChatbotOut:
    """Map ORM Chatbot → ChatbotOut (public summary, no tuning knobs)."""
    return ChatbotOut(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        brand_color=c.brand_color,
        llm_provider=c.llm_provider,
        llm_model=c.llm_model,
        has_custom_api_key=c.custom_api_key_encrypted is not None,
        tone_preset=c.tone_preset,
        default_language=c.default_language,
        fallback_language=c.fallback_language,
        widget_style=c.widget_style,
        welcome_message=c.welcome_message,
        input_placeholder=c.input_placeholder,
        memory_mode=c.memory_mode,
        auth_mode=c.auth_mode,
        is_active=c.is_active,
        deployment_status=c.deployment_status,
        total_messages=c.total_messages,
        total_conversations=c.total_conversations,
        resolution_rate=c.resolution_rate,
        avg_response_time_ms=c.avg_response_time_ms,
        avg_confidence_score=c.avg_confidence_score,
        created_at=c.created_at,
        updated_at=c.updated_at,
        last_trained_at=c.last_trained_at,
        last_deployed_at=c.last_deployed_at,
    )


def _to_list_out(c: Chatbot) -> ChatbotListOut:
    return ChatbotListOut(
        id=c.id,
        name=c.name,
        avatar_emoji=c.avatar_emoji,
        brand_color=c.brand_color,
        llm_provider=c.llm_provider,
        llm_model=c.llm_model,
        is_active=c.is_active,
        deployment_status=c.deployment_status,
        total_messages=c.total_messages,
        total_conversations=c.total_conversations,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _build_embed_snippet(chatbot_id: uuid.UUID) -> str:
    from app.config import settings
    return (
        f'<script src="{settings.backend_url}/widget.js" '
        f'data-chatbot-id="{chatbot_id}" async></script>'
    )