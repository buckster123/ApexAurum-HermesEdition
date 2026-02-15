"""
ApexJoule Economy - SQLAlchemy Models

The thermodynamic currency of the Athanor.
1 AJ ~ $0.001 USD compute equivalent.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import String, DateTime, Numeric, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ApexJouleBalance(Base):
    """AJ balance ledger: one row per (user, entity).

    entity_id NULL = user's own balance.
    entity_id 'azoth'|'kether'|'vajra'|'elysian' = agent balance.
    """

    __tablename__ = "apex_joule_balances"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    entity_id: Mapped[Optional[str]] = mapped_column(String(50))
    balance: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    total_earned: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    total_spent: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    love_depth: Mapped[Decimal] = mapped_column(Numeric(10, 4), default=1)
    level: Mapped[int] = mapped_column(Integer, default=1)
    vitality: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_id", "entity_id", name="uq_ajb_user_entity"),
        Index("idx_ajb_user_entity", "user_id", "entity_id"),
    )

    user = relationship("User", back_populates="aj_balances")

    def __repr__(self):
        entity = self.entity_id or "user"
        return f"<AJBalance {entity}: {self.balance} AJ>"


class ApexJouleTransaction(Base):
    """Append-only audit trail for all AJ movements."""

    __tablename__ = "apex_joule_transactions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    from_entity: Mapped[Optional[str]] = mapped_column(String(50))
    to_entity: Mapped[Optional[str]] = mapped_column(String(50))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    tx_type: Mapped[str] = mapped_column(String(30))  # earn, spend, tip, a2a_trade, quest, purchase
    reason: Mapped[Optional[str]] = mapped_column(String(255))

    # Computation audit trail
    e_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    w_output: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    kappa: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    l_multiplier: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4))
    c_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))
    d_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3))

    # Context
    conversation_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True))
    message_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True))
    operation_type: Mapped[Optional[str]] = mapped_column(String(50))
    provider: Mapped[Optional[str]] = mapped_column(String(30))
    model_used: Mapped[Optional[str]] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_ajt_user_time", "user_id", "created_at"),
        Index("idx_ajt_type", "tx_type"),
    )

    def __repr__(self):
        return f"<AJTx {self.tx_type}: {self.amount} AJ>"


class LoveScore(Base):
    """Love scoring history — C/D breakdown per interaction."""

    __tablename__ = "love_scores"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
    )
    agent_id: Mapped[str] = mapped_column(String(50))
    interaction_type: Mapped[Optional[str]] = mapped_column(String(30))
    c_score: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    d_score: Mapped[Decimal] = mapped_column(Numeric(4, 3))
    c_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)
    d_breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)
    love_depth_before: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    love_depth_after: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_ls_agent_time", "user_id", "agent_id", "created_at"),
    )

    def __repr__(self):
        return f"<LoveScore {self.agent_id}: C={self.c_score} D={self.d_score}>"
