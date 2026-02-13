"""
User Progression Model - Quest Engine

Tracks quest state, milestones, feature unlocks, and stats
for users on the gamified Quest tier path.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import String, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base


class UserProgression(Base):
    """
    Quest progression tracking for gamified tier users.

    Classic tier users may also have a progression record
    (quest_active=False) for cosmetic E5 stat syncing.
    """

    __tablename__ = "user_progressions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    # User relationship (one progression per user)
    user_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False
    )

    # Quest state
    quest_active: Mapped[bool] = mapped_column(Boolean, default=False)
    quest_stage: Mapped[str] = mapped_column(String(20), default="seeker")
    quest_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Milestone tracking (JSONB for flexibility)
    milestones_completed: Mapped[list] = mapped_column(JSONB, default=list)
    features_unlocked: Mapped[list] = mapped_column(JSONB, default=list)

    # Stats (server-side mirror of E5 localStorage)
    agent_stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    zone_stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    achievements: Mapped[list] = mapped_column(JSONB, default=list)
    total_tasks: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationship
    user = relationship("User", back_populates="progression")

    def __repr__(self):
        stage = self.quest_stage if self.quest_active else "inactive"
        return f"<UserProgression {stage} for user {self.user_id}>"
