"""
Solana Payment Model — On-chain payment verification records.

Tracks SOL/USDC/SPL token payments and their AJ credit fulfillment.
tx_signature is UNIQUE — the idempotency key preventing double-credits.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import String, DateTime, Numeric, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SolanaPayment(Base):
    """One row per payment request. Status tracks lifecycle:
    pending -> confirmed -> credited (happy path)
    pending -> expired (30 min timeout)
    pending -> failed (verification failure)
    """

    __tablename__ = "solana_payments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Solana Pay reference — random pubkey for tx discovery
    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # On-chain data (populated after confirmation)
    tx_signature: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, nullable=True
    )
    slot: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Payment details
    amount_decimal: Mapped[Decimal] = mapped_column(Numeric(18, 9))  # High precision for SOL
    token_mint: Mapped[str] = mapped_column(String(64))  # "SOL", USDC mint, or any SPL token
    token_symbol: Mapped[str] = mapped_column(String(10))  # "SOL", "USDC", etc.

    # Conversion snapshot (frozen at payment creation time)
    sol_price_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4), nullable=True)
    usd_equivalent: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    aj_credited: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, confirmed, credited, failed, expired
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_sp_user_status", "user_id", "status"),
        Index("idx_sp_created", "created_at"),
    )

    def __repr__(self):
        return f"<SolanaPayment {self.token_symbol} {self.amount_decimal} -> {self.aj_credited} AJ [{self.status}]>"
