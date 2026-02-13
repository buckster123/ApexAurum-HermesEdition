"""
Add user_progressions table for Quest Engine

Tracks quest state, milestones, feature unlocks, and gamification stats
for users on the Quest tier path. Also usable by classic tier users
for server-side stat persistence.

Revision ID: 003_progression
Revises: 002_billing_tables
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = '003_progression'
down_revision = '002_billing_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create user_progressions table."""

    op.create_table(
        'user_progressions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), unique=True, index=True, nullable=False),

        # Quest state
        sa.Column('quest_active', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('quest_stage', sa.String(20), nullable=False, server_default='seeker'),
        sa.Column('quest_started_at', sa.DateTime(timezone=True), nullable=True),

        # Milestone tracking (JSONB)
        sa.Column('milestones_completed', JSONB, nullable=False, server_default='[]'),
        sa.Column('features_unlocked', JSONB, nullable=False, server_default='[]'),

        # Stats (server-side mirror of E5 localStorage)
        sa.Column('agent_stats', JSONB, nullable=False, server_default='{}'),
        sa.Column('zone_stats', JSONB, nullable=False, server_default='{}'),
        sa.Column('achievements', JSONB, nullable=False, server_default='[]'),
        sa.Column('total_tasks', sa.Integer, nullable=False, server_default='0'),

        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop user_progressions table."""
    op.drop_table('user_progressions')
