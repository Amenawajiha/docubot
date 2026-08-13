"""
Chatbot service — create, list, get, update, delete, deploy/pause chatbots.
"""

from __future__ import annotations

import uuid

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
    ChatbotUpdate,
)
from app.utils.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.utils.security import encrypt_api_key, hash_password


_ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2, "owner": 3}


class ChatbotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.bot_repo = ChatbotRepository(session)
        self.ws_repo = WorkspaceRepository(session)
        self.mem_repo = WorkspaceMemberRepository(session)

    # ── CRUD ──────────────────────────────────────────────────────────────────

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

        # Encrypt custom API key if provided
        encrypted_key: str | None = None
        if data.custom_api_key:
            encrypted_key = encrypt_api_key(data.custom_api_key)

        # Hash passcode if provided
        passcode_hash: str | None = None
        if data.passcode:
            passcode_hash = hash_password(data.passcode)

        chatbot = await self.bot_repo.create(
            workspace_id=workspace_id,
            name=data.name,
            brand_color=data.brand_color,
            llm_provider=data.llm_provider,
            llm_model=data.llm_model,
            custom_api_key_encrypted=encrypted_key,
            tone_preset=data.tone_preset,
            default_language=data.default_language,
            fallback_language=data.fallback_language,
            widget_style=data.widget_style,
            welcome_message=data.welcome_message,
            input_placeholder=data.input_placeholder,
            memory_mode=data.memory_mode,
            auth_mode=data.auth_mode,
            passcode_hash=passcode_hash,
        )

        return _to_out(chatbot)

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

    async def update(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        data: ChatbotUpdate,
        actor: User,
    ) -> ChatbotOut:
        await self._require_role(workspace_id, actor.id, "editor")
        chatbot = await self._require_chatbot(workspace_id, chatbot_id)

        updates: dict = {}
        for field in [
            "name", "brand_color", "llm_provider", "llm_model",
            "tone_preset", "custom_system_prompt", "default_language",
            "fallback_language", "widget_style", "welcome_message",
            "input_placeholder", "memory_mode", "auth_mode",
            "deployment_status", "is_active",
        ]:
            val = getattr(data, field, None)
            if val is not None:
                updates[field] = val

        # Re-encrypt API key if updated
        if data.custom_api_key is not None:
            updates["custom_api_key_encrypted"] = (
                encrypt_api_key(data.custom_api_key) if data.custom_api_key else None
            )

        # Re-hash passcode if updated
        if data.passcode is not None:
            updates["passcode_hash"] = (
                hash_password(data.passcode) if data.passcode else None
            )

        chatbot = await self.bot_repo.update(chatbot, **updates)
        return _to_out(chatbot)

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

        from datetime import datetime, timezone
        chatbot = await self.bot_repo.update(
            chatbot,
            is_active=True,
            deployment_status="published",
            last_deployed_at=datetime.now(timezone.utc),
        )

        from app.core.deployment.service import DeploymentService
        from app.schemas.deployment import CreateChannelRequest
        from app.config import settings
        
        ch_service = DeploymentService(self.session)
        channels = await ch_service.ch_repo.list_for_chatbot(chatbot.id)
        widget_channel = next((c for c in channels if c.channel_type == "widget"), None)
        
        if not widget_channel:
            widget_channel = await ch_service.create_channel(
                workspace_id,
                chatbot.id,
                CreateChannelRequest(
                    channel_type="widget",
                    channel_name="Web Widget",
                    config={},
                    allowed_domains=[]
                ),
                actor.id
            )

        ws = await self.ws_repo.get_by_id_active(workspace_id)
        workspace_slug = ws.slug if ws else str(workspace_id)

        script_src = f"{settings.frontend_url}/widget.js"
        embed_script = (
            f'<script\n'
            f'  src="{script_src}"\n'
            f'  data-chatbot-id="{chatbot_id}"\n'
            f'  data-workspace="{workspace_slug}"\n'
            f'  data-channel-id="{widget_channel.id}"\n'
            f'  async>\n'
            f'</script>'
        )

        return ChatbotDeployResponse(
            id=chatbot.id,
            deployment_status=chatbot.deployment_status,
            is_active=chatbot.is_active,
            last_deployed_at=chatbot.last_deployed_at,
            embed_snippet=embed_script,
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
        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        effective = "owner" if ws and ws.owner_id == user_id else member.role
        if _ROLE_RANK.get(effective, -1) < _ROLE_RANK.get(min_role, 99):
            raise ForbiddenError(
                f"This action requires at least the '{min_role}' role."
            )


# ── Module-level helpers ──────────────────────────────────────────────────────

def _mask_api_key(raw_key: str) -> str:
    if len(raw_key) <= 8:
        return "***"
    return f"{raw_key[:4]}...{raw_key[-4:]}"

def _to_out(c: Chatbot) -> ChatbotOut:
    masked_key = None
    if c.custom_api_key_encrypted:
        from app.utils.security import decrypt_api_key
        try:
            raw_key = decrypt_api_key(c.custom_api_key_encrypted)
            masked_key = _mask_api_key(raw_key)
        except Exception:
            masked_key = "***"

    return ChatbotOut(
        id=c.id,
        workspace_id=c.workspace_id,
        name=c.name,
        brand_color=c.brand_color,
        llm_provider=c.llm_provider,
        llm_model=c.llm_model,
        has_custom_api_key=c.custom_api_key_encrypted is not None,
        custom_api_key_masked=masked_key,
        tone_preset=c.tone_preset,
        custom_system_prompt=c.custom_system_prompt,
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
        brand_color=c.brand_color,
        llm_provider=c.llm_provider,
        llm_model=c.llm_model,
        custom_system_prompt=c.custom_system_prompt,
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


async def purge_expired_chatbots(session: AsyncSession) -> int:
    """
    Finds all soft-deleted chatbots where deleted_at < NOW - retention_days,
    clears their Qdrant collections, deletes MinIO docs, and hard-deletes them from SQL.
    """
    import logging
    from datetime import datetime, timezone, timedelta
    from sqlalchemy import select
    from app.config import settings
    from app.data.models import Chatbot, ChatbotDocument
    from app.infrastructure.storage.s3_client import delete_file
    from app.infrastructure.queue.celery_app import celery_app, TASK_CLEAR_COLLECTION
    from app.core.knowledge.service import collection_name

    _log = logging.getLogger(__name__)
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.chatbot_retention_days)

    # 1. Find expired chatbots
    stmt = select(Chatbot).where(Chatbot.deleted_at <= cutoff)
    result = await session.execute(stmt)
    expired_bots = result.scalars().all()

    deleted_count = 0
    for bot in expired_bots:
        _log.info(f"Purging expired chatbot: {bot.id} (soft-deleted at {bot.deleted_at})")

        # 2. Delete all S3 files for this bot
        docs_stmt = select(ChatbotDocument).where(ChatbotDocument.chatbot_id == bot.id)
        docs_res = await session.execute(docs_stmt)
        for doc in docs_res.scalars():
            if doc.storage_key:
                try:
                    await delete_file(doc.storage_key)
                except Exception as e:
                    _log.warning(f"Failed to delete S3 file {doc.storage_key}: {e}")

        # 3. Clear Qdrant collection
        celery_app.send_task(
            TASK_CLEAR_COLLECTION,
            kwargs={
                "workspace_id": str(bot.workspace_id),
                "chatbot_id": str(bot.id),
                "collection_name": collection_name(bot.workspace_id, bot.id),
            },
        )

        # 4. Hard-delete from SQL
        await session.delete(bot)
        deleted_count += 1

    if deleted_count > 0:
        await session.commit()
    
    return deleted_count
