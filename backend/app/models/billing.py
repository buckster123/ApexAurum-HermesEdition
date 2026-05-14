"""
Billing Models - Local Mode (Stripped)

Minimal subscription tracking for local-only use.
No Stripe, no credits, no coupons.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Subscription(Base):
    """Minimal subscription for local mode. Always active, unlimited."""

    __tablename__ = "subscriptions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        unique=True,
        index=True
    )

    tier: Mapped[str] = mapped_column(String(20), default="local")
    status: Mapped[str] = mapped_column(String(20), default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self):
        return f"<Subscription local for user {self.user_id}>"
