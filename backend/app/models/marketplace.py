"""
Marketplace Models — Agent bundle listings and purchases.

Enables users to share and sell exported agent configurations.
All transactions denominated in AJ.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import String, Text, DateTime, Numeric, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketplaceListing(Base):
    """An agent bundle listed for sale or free sharing."""

    __tablename__ = "marketplace_listings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    seller_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Listing metadata
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_id: Mapped[str] = mapped_column(String(100))  # Source agent identity
    tags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)

    # The actual bundle (stored as JSONB)
    bundle: Mapped[dict] = mapped_column(JSONB)

    # Pricing
    price_aj: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)  # 0 = free

    # Stats
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    rating_sum: Mapped[int] = mapped_column(Integer, default=0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    # Lifecycle
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, delisted, flagged
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_ml_status_created", "status", "created_at"),
        Index("idx_ml_agent", "agent_id"),
    )

    def __repr__(self):
        return f"<Listing '{self.title}' ({self.price_aj} AJ)>"


class MarketplacePurchase(Base):
    """Records of bundle purchases/downloads."""

    __tablename__ = "marketplace_purchases"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    listing_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        index=True,
    )
    buyer_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    price_aj: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 1-5
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_mp_buyer_listing", "buyer_id", "listing_id"),
    )

    def __repr__(self):
        return f"<Purchase listing={self.listing_id} buyer={self.buyer_id} {self.price_aj} AJ>"
