"""
Solana Pay API — Crypto payment endpoints for AJ purchases.

Endpoints:
- POST /solana/create-payment  — Generate payment request with Solana Pay URI
- GET  /solana/check-payment/{reference} — Poll for on-chain confirmation
- GET  /solana/rates — Current SOL/USD and AJ conversion rates
- GET  /solana/history — User's crypto payment history
"""

import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.auth.deps import get_current_user
from app.config import get_settings
from app.services.solana.payment_service import SolanaPaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/solana", tags=["Solana Pay"])


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class CreatePaymentRequest(BaseModel):
    amount_usd: float = Field(..., gt=0, le=1000, description="USD amount to pay")
    token: str = Field(default="SOL", description="Token to pay with: SOL or USDC")


class CreatePaymentResponse(BaseModel):
    reference: str
    solana_url: str
    aj_amount: float
    amount_token: float
    token: str
    usd_equivalent: float
    status: str
    expires_at: str


class CheckPaymentResponse(BaseModel):
    status: str  # pending, confirmed, credited, expired, failed, not_found
    aj_credited: Optional[float] = None
    tx_signature: Optional[str] = None
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/create-payment", response_model=CreatePaymentResponse)
async def create_payment(
    request: CreatePaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a Solana Pay payment request.

    Returns a `solana:` URI for the wallet to scan/click,
    plus a reference ID to poll for confirmation.
    """
    settings = get_settings()
    if not settings.solana_recipient_address:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Solana payments are not configured yet.",
        )

    if request.token not in ("SOL", "USDC"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token must be SOL or USDC.",
        )

    try:
        service = SolanaPaymentService(db)
        result = await service.create_payment_request(
            user_id=user.id,
            amount_usd=Decimal(str(request.amount_usd)),
            token=request.token,
        )
        await db.commit()
        return CreatePaymentResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Create payment error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment request.",
        )


@router.get("/check-payment/{reference}", response_model=CheckPaymentResponse)
async def check_payment(
    reference: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll for payment confirmation.

    Frontend calls this every 3s until status is 'credited' or 'expired'.
    """
    try:
        service = SolanaPaymentService(db)
        result = await service.check_payment(reference)
        await db.commit()
        return CheckPaymentResponse(**result)

    except Exception as e:
        logger.error(f"Check payment error for {reference}: {e}")
        return CheckPaymentResponse(status="error", error="Failed to check payment status")


@router.get("/rates")
async def get_rates(
    db: AsyncSession = Depends(get_db),
):
    """Get current SOL/USD price and AJ conversion rates.

    No auth required — public pricing info.
    """
    try:
        service = SolanaPaymentService(db)
        return await service.get_rates()
    except Exception as e:
        logger.error(f"Rates fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch current rates.",
        )


@router.get("/history")
async def get_payment_history(
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get authenticated user's Solana payment history."""
    service = SolanaPaymentService(db)
    payments = await service.get_payment_history(user.id, limit=limit)
    return {"payments": payments, "total": len(payments)}
