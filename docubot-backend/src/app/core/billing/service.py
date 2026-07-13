"""Billing service — Phase 8."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.models import Invoice, InvoiceLineItem, Plan, Subscription
from app.data.repositories.base import BaseRepository
from app.data.repositories.chat_repo import UsageLogRepository
from app.data.repositories.chatbot_repo import ChatbotRepository
from app.data.repositories.workspace_repo import WorkspaceRepository
from app.schemas.billing import (
    ChangePlanRequest,
    InvoiceOut,
    LineItemOut,
    PlanOut,
    SubscriptionOut,
    UsageSummaryOut,
)
from app.utils.exceptions import BadRequestError, ForbiddenError, NotFoundError


class PlanRepository(BaseRepository[Plan]):
    model = Plan

    async def list_active(self) -> list[Plan]:
        result = await self.session.execute(
            select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_monthly_usd)
        )
        return list(result.scalars().all())

    async def get_by_slug(self, slug: str) -> Plan | None:
        result = await self.session.execute(
            select(Plan).where(Plan.slug == slug, Plan.is_active.is_(True))
        )
        return result.scalar_one_or_none()


class SubscriptionRepository(BaseRepository[Subscription]):
    model = Subscription

    async def get_for_workspace(self, workspace_id: uuid.UUID) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()


class InvoiceRepository(BaseRepository[Invoice]):
    model = Invoice

    async def list_for_workspace(
        self, workspace_id: uuid.UUID, limit: int = 24
    ) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .where(Invoice.workspace_id == workspace_id)
            .order_by(Invoice.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_items(
        self, invoice_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Invoice | None:
        result = await self.session.execute(
            select(Invoice).where(
                Invoice.id == invoice_id,
                Invoice.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def next_invoice_number(self) -> str:
        from sqlalchemy import func
        result = await self.session.execute(select(func.count(Invoice.id)))
        count = result.scalar_one() + 1
        return f"INV-{datetime.now(timezone.utc).year}-{count:05d}"


class InvoiceLineItemRepository(BaseRepository[InvoiceLineItem]):
    model = InvoiceLineItem

    async def list_for_invoice(self, invoice_id: uuid.UUID) -> list[InvoiceLineItem]:
        result = await self.session.execute(
            select(InvoiceLineItem).where(
                InvoiceLineItem.invoice_id == invoice_id
            )
        )
        return list(result.scalars().all())


class BillingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db       = db
        self.plan_repo = PlanRepository(db)
        self.sub_repo  = SubscriptionRepository(db)
        self.inv_repo  = InvoiceRepository(db)
        self.item_repo = InvoiceLineItemRepository(db)
        self.ws_repo   = WorkspaceRepository(db)
        self.bot_repo  = ChatbotRepository(db)
        self.use_repo  = UsageLogRepository(db)

    # ── Plans ─────────────────────────────────────────────────────────────────

    async def list_plans(self) -> list[PlanOut]:
        plans = await self.plan_repo.list_active()
        return [self._plan_out(p) for p in plans]

    # ── Subscription ──────────────────────────────────────────────────────────

    async def get_subscription(
        self, workspace_id: uuid.UUID, actor_id: uuid.UUID
    ) -> SubscriptionOut:
        await self._require_member(workspace_id, actor_id)
        sub = await self.sub_repo.get_for_workspace(workspace_id)
        if not sub:
            raise NotFoundError("Subscription")
        plan = await self.plan_repo.get_by_id(sub.plan_id)
        return self._sub_out(sub, plan.name if plan else "Unknown")

    async def change_plan(
        self,
        workspace_id: uuid.UUID,
        data: ChangePlanRequest,
        actor_id: uuid.UUID,
    ) -> SubscriptionOut:
        """Change the workspace plan. In production, delegate to Stripe webhook."""
        await self._require_owner(workspace_id, actor_id)

        plan = await self.plan_repo.get_by_id(data.plan_id)
        if not plan:
            raise NotFoundError("Plan")

        sub = await self.sub_repo.get_for_workspace(workspace_id)
        now = datetime.now(timezone.utc)

        if sub:
            sub = await self.sub_repo.update(
                sub,
                plan_id=data.plan_id,
                billing_cycle=data.billing_cycle,
                updated_at=now,
            )
        else:
            sub = await self.sub_repo.create(
                workspace_id=workspace_id,
                plan_id=data.plan_id,
                billing_cycle=data.billing_cycle,
                status="active",
                current_period_start=now,
            )

        # Mirror limits back to workspace row
        await self.ws_repo.update(
            await self.ws_repo.get_by_id_active(workspace_id),
            plan_tier=plan.slug,
            monthly_message_limit=plan.monthly_message_limit,
            chatbot_limit=plan.chatbot_limit,
            storage_limit_mb=plan.storage_limit_mb,
        )

        return self._sub_out(sub, plan.name)

    # ── Invoices ──────────────────────────────────────────────────────────────

    async def list_invoices(
        self, workspace_id: uuid.UUID, actor_id: uuid.UUID
    ) -> list[InvoiceOut]:
        await self._require_member(workspace_id, actor_id)
        invoices = await self.inv_repo.list_for_workspace(workspace_id)
        result = []
        for inv in invoices:
            items = await self.item_repo.list_for_invoice(inv.id)
            result.append(self._invoice_out(inv, items))
        return result

    async def get_invoice(
        self,
        workspace_id: uuid.UUID,
        invoice_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> InvoiceOut:
        await self._require_member(workspace_id, actor_id)
        inv = await self.inv_repo.get_with_items(invoice_id, workspace_id)
        if not inv:
            raise NotFoundError("Invoice")
        items = await self.item_repo.list_for_invoice(inv.id)
        return self._invoice_out(inv, items)

    async def generate_monthly_invoice(
        self, workspace_id: uuid.UUID
    ) -> InvoiceOut:
        """
        Generate an invoice for the current month.
        Called by a scheduled Celery task at month-end.
        In production this would be replaced by Stripe's invoice generation.
        """
        sub = await self.sub_repo.get_for_workspace(workspace_id)
        if not sub:
            raise BadRequestError("No active subscription for this workspace.")

        plan = await self.plan_repo.get_by_id(sub.plan_id)
        if not plan:
            raise NotFoundError("Plan")

        now   = datetime.now(timezone.utc)
        start = date(now.year, now.month, 1)
        # Last day of the month
        if now.month == 12:
            end = date(now.year + 1, 1, 1)
        else:
            end = date(now.year, now.month + 1, 1)

        usage = await self.use_repo.get_monthly_usage(
            workspace_id, now.year, now.month
        )

        base_price = (
            plan.price_yearly_usd / 12
            if sub.billing_cycle == "yearly" and plan.price_yearly_usd
            else plan.price_monthly_usd
        )

        # Overage calculation
        msg_overage_usd = Decimal("0")
        msg_limit = plan.monthly_message_limit
        msg_used  = usage["message_count"]
        if msg_used > msg_limit:
            overage_msgs = msg_used - msg_limit
            # $0.002 per extra message
            msg_overage_usd = Decimal(str(overage_msgs)) * Decimal("0.002")

        subtotal = base_price + msg_overage_usd
        tax      = subtotal * Decimal("0.00")   # no tax for now
        total    = subtotal + tax

        inv_number = await self.inv_repo.next_invoice_number()
        inv = await self.inv_repo.create(
            workspace_id=workspace_id,
            subscription_id=sub.id,
            invoice_number=inv_number,
            status="open",
            subtotal_usd=str(subtotal),
            tax_usd=str(tax),
            total_usd=str(total),
            period_start=start,
            period_end=end,
        )

        # Base subscription line item
        base_item = await self.item_repo.create(
            invoice_id=inv.id,
            description=f"{plan.name} — {sub.billing_cycle.capitalize()} subscription",
            quantity=1,
            unit_price=str(base_price),
            amount_usd=str(base_price),
            item_type="subscription",
        )
        items = [base_item]

        if msg_overage_usd > 0:
            overage_item = await self.item_repo.create(
                invoice_id=inv.id,
                description=f"Message overage ({msg_used - msg_limit:,} extra messages)",
                quantity=msg_used - msg_limit,
                unit_price="0.002",
                amount_usd=str(msg_overage_usd),
                item_type="overage_messages",
            )
            items.append(overage_item)

        return self._invoice_out(inv, items)

    # ── Usage summary ─────────────────────────────────────────────────────────

    async def get_usage_summary(
        self, workspace_id: uuid.UUID, actor_id: uuid.UUID
    ) -> UsageSummaryOut:
        await self._require_member(workspace_id, actor_id)
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        if not ws:
            raise NotFoundError("Workspace")

        sub  = await self.sub_repo.get_for_workspace(workspace_id)
        plan = await self.plan_repo.get_by_id(sub.plan_id) if sub else None

        now   = datetime.now(timezone.utc)
        usage = await self.use_repo.get_monthly_usage(
            workspace_id, now.year, now.month
        )
        chatbot_count = await self.bot_repo.count_active_for_workspace(workspace_id)

        # Storage — sum from chatbot_documents
        from sqlalchemy import func
        from app.data.models import ChatbotDocument
        storage_result = await self.db.execute(
            select(func.coalesce(
                func.sum(ChatbotDocument.file_size_bytes), 0
            )).where(
                ChatbotDocument.workspace_id == workspace_id,
                ChatbotDocument.deleted_at.is_(None),
            )
        )
        storage_bytes = storage_result.scalar_one()
        storage_mb    = round(storage_bytes / 1_048_576, 2)

        msg_limit    = ws.monthly_message_limit
        msg_used     = usage["message_count"]
        chatbot_lim  = ws.chatbot_limit
        storage_lim  = ws.storage_limit_mb

        return UsageSummaryOut(
            workspace_id=workspace_id,
            plan_name=plan.name if plan else ws.plan_tier,
            billing_cycle=sub.billing_cycle if sub else "monthly",
            period_start=sub.current_period_start.date() if sub and sub.current_period_start else None,
            period_end=sub.current_period_end.date() if sub and sub.current_period_end else None,
            messages_used=msg_used,
            messages_limit=msg_limit,
            messages_pct=round(msg_used / msg_limit * 100, 1) if msg_limit else 0.0,
            chatbots_used=chatbot_count,
            chatbots_limit=chatbot_lim,
            storage_used_mb=storage_mb,
            storage_limit_mb=storage_lim,
            tokens_used=usage["tokens_total"],
            estimated_cost_usd=usage["cost_usd"],
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _require_member(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        from app.data.repositories.workspace_repo import WorkspaceMemberRepository
        mem = await WorkspaceMemberRepository(self.db).get_membership(workspace_id, user_id)
        if not mem or mem.joined_at is None:
            raise ForbiddenError("You are not a member of this workspace.")

    async def _require_owner(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> None:
        ws = await self.ws_repo.get_by_id_active(workspace_id)
        if not ws or ws.owner_id != user_id:
            raise ForbiddenError("Only the workspace owner can change billing.")

    @staticmethod
    def _plan_out(p: Plan) -> PlanOut:
        return PlanOut(
            id=p.id, name=p.name, slug=p.slug,
            price_monthly_usd=p.price_monthly_usd,
            price_yearly_usd=p.price_yearly_usd,
            chatbot_limit=p.chatbot_limit,
            monthly_message_limit=p.monthly_message_limit,
            storage_limit_mb=p.storage_limit_mb,
            team_member_limit=p.team_member_limit,
            features=p.features or [],
            is_active=p.is_active,
        )

    @staticmethod
    def _sub_out(s: Subscription, plan_name: str) -> SubscriptionOut:
        return SubscriptionOut(
            id=s.id, workspace_id=s.workspace_id, plan_id=s.plan_id,
            plan_name=plan_name, status=s.status,
            billing_cycle=s.billing_cycle,
            current_period_start=s.current_period_start,
            current_period_end=s.current_period_end,
            trial_ends_at=s.trial_ends_at,
            canceled_at=s.canceled_at,
        )

    @staticmethod
    def _invoice_out(
        inv: Invoice, items: list[InvoiceLineItem]
    ) -> InvoiceOut:
        return InvoiceOut(
            id=inv.id, workspace_id=inv.workspace_id,
            invoice_number=inv.invoice_number, status=inv.status,
            currency=inv.currency,
            subtotal_usd=inv.subtotal_usd, tax_usd=inv.tax_usd,
            total_usd=inv.total_usd,
            period_start=inv.period_start, period_end=inv.period_end,
            paid_at=inv.paid_at, due_at=inv.due_at,
            created_at=inv.created_at,
            line_items=[
                LineItemOut(
                    id=it.id, description=it.description,
                    quantity=it.quantity, unit_price=it.unit_price,
                    amount_usd=it.amount_usd, item_type=it.item_type,
                )
                for it in items
            ],
        )