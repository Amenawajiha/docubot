"""Deployment channels service — Phase 7."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import DeploymentChannel
from app.data.repositories.base import BaseRepository
from app.data.repositories.chatbot_repo import ChatbotRepository
from app.data.repositories.workspace_repo import (
    WorkspaceMemberRepository,
    WorkspaceRepository,
)
from app.schemas.deployment import (
    ChannelOut,
    CreateChannelRequest,
    UpdateChannelRequest,
    WidgetEmbedOut,
)
from app.utils.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.utils.security import generate_api_key, hash_password

_ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2}


class DeploymentChannelRepository(BaseRepository[DeploymentChannel]):
    model = DeploymentChannel

    async def list_for_chatbot(
        self, chatbot_id: uuid.UUID
    ) -> list[DeploymentChannel]:
        result = await self.session.execute(
            select(DeploymentChannel).where(
                DeploymentChannel.chatbot_id == chatbot_id,
                DeploymentChannel.is_active.is_(True),
            )
        )
        return list(result.scalars().all())

    async def get_for_chatbot(
        self, channel_id: uuid.UUID, chatbot_id: uuid.UUID
    ) -> DeploymentChannel | None:
        result = await self.session.execute(
            select(DeploymentChannel).where(
                DeploymentChannel.id == channel_id,
                DeploymentChannel.chatbot_id == chatbot_id,
            )
        )
        return result.scalar_one_or_none()


def _to_out(ch: DeploymentChannel) -> ChannelOut:
    return ChannelOut(
        id=ch.id,
        workspace_id=ch.workspace_id,
        chatbot_id=ch.chatbot_id,
        channel_type=ch.channel_type,
        channel_name=ch.channel_name,
        config=ch.config or {},
        allowed_domains=ch.allowed_domains or [],
        is_active=ch.is_active,
        has_api_key=ch.api_key_hash is not None,
        created_at=ch.created_at,
        updated_at=ch.updated_at,
    )


class DeploymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db       = db
        self.ch_repo  = DeploymentChannelRepository(db)
        self.bot_repo = ChatbotRepository(db)
        self.ws_repo  = WorkspaceRepository(db)
        self.mem_repo = WorkspaceMemberRepository(db)

    async def list_channels(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> list[ChannelOut]:
        await self._require_member(workspace_id, actor_id)
        await self._require_chatbot(workspace_id, chatbot_id)
        channels = await self.ch_repo.list_for_chatbot(chatbot_id)
        return [_to_out(ch) for ch in channels]

    async def create_channel(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        data: CreateChannelRequest,
        actor_id: uuid.UUID,
    ) -> ChannelOut:
        await self._require_role(workspace_id, actor_id, "editor")
        chatbot = await self._require_chatbot(workspace_id, chatbot_id)
        if chatbot.deployment_status not in ("published", "paused"):
            raise BadRequestError(
                "Chatbot must be published before adding deployment channels."
            )

        api_key_prefix = api_key_hash = None
        raw_key = None
        if data.channel_type == "api":
            raw_key, api_key_prefix, api_key_hash = generate_api_key()

        ch = await self.ch_repo.create(
            workspace_id=workspace_id,
            chatbot_id=chatbot_id,
            channel_type=data.channel_type,
            channel_name=data.channel_name,
            config=data.config,
            allowed_domains=data.allowed_domains,
            api_key_prefix=api_key_prefix,
            api_key_hash=api_key_hash,
        )
        out = _to_out(ch)
        # Attach the raw key once — only on creation
        if raw_key:
            out = out.model_copy(update={"has_api_key": True})
            # Attach raw key as a non-model attribute for the response layer
            # The route handler adds it to the response dict directly
            setattr(out, "_raw_api_key", raw_key)
        return out

    async def update_channel(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        channel_id: uuid.UUID,
        data: UpdateChannelRequest,
        actor_id: uuid.UUID,
    ) -> ChannelOut:
        await self._require_role(workspace_id, actor_id, "editor")
        ch = await self.ch_repo.get_for_chatbot(channel_id, chatbot_id)
        if not ch:
            raise NotFoundError("DeploymentChannel")

        updates: dict = {}
        if data.channel_name is not None:
            updates["channel_name"] = data.channel_name
        if data.config is not None:
            updates["config"] = data.config
        if data.allowed_domains is not None:
            updates["allowed_domains"] = data.allowed_domains
        if data.is_active is not None:
            updates["is_active"] = data.is_active

        ch = await self.ch_repo.update(ch, **updates)
        return _to_out(ch)

    async def delete_channel(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        channel_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> None:
        await self._require_role(workspace_id, actor_id, "admin")
        ch = await self.ch_repo.get_for_chatbot(channel_id, chatbot_id)
        if not ch:
            raise NotFoundError("DeploymentChannel")
        await self.ch_repo.delete(ch)

    async def get_embed_snippet(
        self,
        workspace_id: uuid.UUID,
        chatbot_id: uuid.UUID,
        channel_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> WidgetEmbedOut:
        await self._require_member(workspace_id, actor_id)
        ch = await self.ch_repo.get_for_chatbot(channel_id, chatbot_id)
        if not ch or ch.channel_type != "widget":
            raise NotFoundError("Widget channel")

        ws = await self.ws_repo.get_by_id_active(workspace_id)
        workspace_slug = ws.slug if ws else str(workspace_id)

        from app.config import settings
        widget_url = f"{settings.backend_url}/api/v1/chatbot/{workspace_slug}/{chatbot_id}"
        script_src = f"{settings.frontend_url}/widget.js"

        embed_script = (
            f'<script \n'
            f'        src="{script_src}" \n'
            f'        data-chatbot-id="{chatbot_id}" \n'
            f'        data-workspace="{workspace_slug}" \n'
            f'        data-channel-id="{channel_id}" \n'
            f'        async>\n'
            f'    </script>'
        )
        embed_div = (
            f'<div id="docubot-chat-{chatbot_id}"></div>'
        )

        return WidgetEmbedOut(
            chatbot_id=chatbot_id,
            channel_id=channel_id,
            widget_url=widget_url,
            embed_script=embed_script,
            embed_div=embed_div,
        )

    async def _require_chatbot(self, workspace_id, chatbot_id):
        bot = await self.bot_repo.get_by_id_in_workspace(chatbot_id, workspace_id)
        if not bot:
            raise NotFoundError("Chatbot")
        return bot

    async def _require_member(self, workspace_id, user_id):
        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")

    async def _require_role(self, workspace_id, user_id, min_role):
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        if ws and ws.owner_id == user_id:
            return
        member = await self.mem_repo.get_membership(workspace_id, user_id)
        if not member or member.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")
        if _ROLE_RANK.get(member.role, -1) < _ROLE_RANK.get(min_role, 99):
            raise ForbiddenError(f"Requires at least '{min_role}' role.")