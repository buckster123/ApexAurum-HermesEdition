"""
Billing API - Local Mode Stub

Returns unlimited local status. No Stripe, no checkout, no webhooks.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.billing import BillingService

router = APIRouter()


@router.get("/status", tags=["Billing"])
async def get_billing_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's billing status. Always returns unlimited in local mode."""
    billing = BillingService(db)
    return await billing.get_subscription_status(current_user.id)
