"""
Multiverse Models — Cross-user portal system for the Athaverse.

5 tables:
  - village_profiles: Public village identity + cached stats
  - portals: Bidirectional portal links between users
  - portal_visits: Visit session tracking
  - cross_village_transactions: AJ flows (tolls, tips, gifts)
  - friend_connections: Social layer for portal access control

"The Athanor's flame illuminates not one village, but a constellation of worlds."
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4
from decimal import Decimal

from sqlalchemy import (
    String, Text, DateTime, Numeric, Integer, Boolean,
    ForeignKey, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VillageProfile(Base):
    """Public identity for a user's village in the multiverse."""

    __tablename__ = "village_profiles"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    # Identity
    name: Mapped[str] = mapped_column(String(100), default="Unnamed Village")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    theme: Mapped[str] = mapped_column(String(50), default="default")

    # Access control
    portal_access: Mapped[str] = mapped_column(
        String(20), default="public"
    )  # public, friends, private

    # Custom layout overrides (zone renames, custom decorations, etc.)
    layout_config: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)

    # Cached stats (refreshed periodically)
    cached_stats: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict)
    total_visits: Mapped[int] = mapped_column(Integer, default=0)
    total_aj_earned: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)

    # Featured in directory
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_vp_access_visits", "portal_access", "total_visits"),
    )

    def __repr__(self):
        return f"<VillageProfile '{self.name}' user={self.user_id}>"


class Portal(Base):
    """Bidirectional portal link between two users' villages."""

    __tablename__ = "portals"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Always store user_a < user_b for deduplication
    user_a_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    user_b_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Who initiated
    requested_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True))

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, active, closed, expired

    # Toll (set by either user for their side)
    toll_aj_a: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)  # A charges visitors
    toll_aj_b: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)  # B charges visitors

    # Request message
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_portal_users"),
        Index("idx_portal_status", "status"),
    )

    def __repr__(self):
        return f"<Portal {self.user_a_id} <-> {self.user_b_id} [{self.status}]>"


class PortalVisit(Base):
    """Tracks an agent visit session through a portal."""

    __tablename__ = "portal_visits"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    portal_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portals.id", ondelete="CASCADE"),
        index=True,
    )
    visitor_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    host_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    # Which agent is visiting
    agent_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Session state
    status: Mapped[str] = mapped_column(
        String(20), default="active"
    )  # active, ended, timed_out

    # AJ toll paid for this visit
    toll_paid: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)

    # Activity log (zones visited, interactions)
    activity_log: Mapped[Optional[dict]] = mapped_column(JSONB, default=list)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_pv_visitor_time", "visitor_id", "started_at"),
        Index("idx_pv_host_time", "host_id", "started_at"),
    )

    def __repr__(self):
        return f"<PortalVisit visitor={self.visitor_id} host={self.host_id} [{self.status}]>"


class CrossVillageTransaction(Base):
    """AJ flows between users via the portal system (tolls, tips, gifts)."""

    __tablename__ = "cross_village_transactions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    from_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    to_user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    fee_amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)  # Platform fee
    tx_type: Mapped[str] = mapped_column(String(20))  # toll, tip, gift

    # Context links
    portal_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portals.id", ondelete="SET NULL"),
        nullable=True,
    )
    visit_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portal_visits.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_cvt_from_time", "from_user_id", "created_at"),
        Index("idx_cvt_to_time", "to_user_id", "created_at"),
        Index("idx_cvt_type", "tx_type"),
    )

    def __repr__(self):
        return f"<CrossVillageTx {self.tx_type}: {self.amount} AJ {self.from_user_id} -> {self.to_user_id}>"


class FriendConnection(Base):
    """Social layer for friends-only portal access."""

    __tablename__ = "friend_connections"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )

    # Always store user_a < user_b for deduplication
    user_a_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    user_b_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )

    requested_by: Mapped[UUID] = mapped_column(UUID(as_uuid=True))

    status: Mapped[str] = mapped_column(
        String(20), default="pending"
    )  # pending, accepted, blocked

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("user_a_id", "user_b_id", name="uq_friend_users"),
        Index("idx_fc_status", "status"),
    )

    def __repr__(self):
        return f"<Friend {self.user_a_id} <-> {self.user_b_id} [{self.status}]>"
