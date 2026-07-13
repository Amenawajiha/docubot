"""Billing endpoints — Phase 8."""

import uuid

from fastapi import APIRouter, status

from app.api.dependencies import DbSession, VerifiedUser
from app.core.billing.service import BillingService
from app.schemas.billing import (
    ChangePlanRequest,
    InvoiceOut,
    PlanOut,
    SubscriptionOut,
    UsageSummaryOut,
)

router = APIRouter(tags=["billing"])


def _svc(session: DbSession) -> BillingService:
    return BillingService(session)


# ── Public plan listing ───────────────────────────────────────────────────────

@router.get(
    "/plans",
    response_model=list[PlanOut],
    summary="List all available plans",
)
async def list_plans(session: DbSession) -> list[PlanOut]:
    return await _svc(session).list_plans()


# ── Workspace billing ─────────────────────────────────────────────────────────

@router.get(
    "/workspaces/{workspace_id}/billing/subscription",
    response_model=SubscriptionOut,
    summary="Get current subscription",
)
async def get_subscription(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> SubscriptionOut:
    return await _svc(session).get_subscription(workspace_id, user.id)


@router.post(
    "/workspaces/{workspace_id}/billing/subscription",
    response_model=SubscriptionOut,
    summary="Change plan (owner only)",
)
async def change_plan(
    workspace_id: uuid.UUID,
    data: ChangePlanRequest,
    user: VerifiedUser,
    session: DbSession,
) -> SubscriptionOut:
    return await _svc(session).change_plan(workspace_id, data, user.id)


@router.get(
    "/workspaces/{workspace_id}/billing/usage",
    response_model=UsageSummaryOut,
    summary="Get current billing period usage summary",
)
async def get_usage_summary(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> UsageSummaryOut:
    return await _svc(session).get_usage_summary(workspace_id, user.id)


@router.get(
    "/workspaces/{workspace_id}/billing/invoices",
    response_model=list[InvoiceOut],
    summary="List invoices",
)
async def list_invoices(
    workspace_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> list[InvoiceOut]:
    return await _svc(session).list_invoices(workspace_id, user.id)


@router.get(
    "/workspaces/{workspace_id}/billing/invoices/{invoice_id}",
    response_model=InvoiceOut,
    summary="Get invoice details",
)
async def get_invoice(
    workspace_id: uuid.UUID,
    invoice_id: uuid.UUID,
    user: VerifiedUser,
    session: DbSession,
) -> InvoiceOut:
    return await _svc(session).get_invoice(workspace_id, invoice_id, user.id)