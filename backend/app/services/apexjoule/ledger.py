"""
ApexJoule Ledger — Balance management and transaction logging.

Pattern matches: BillingService (billing.py:33), UsageService (usage.py:96).
Every AJ movement is double-entry: credit + debit + audit log.
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.apexjoule import ApexJouleBalance, ApexJouleTransaction, LoveScore
from app.services.apexjoule.constants import (
    LEVEL_THRESHOLDS,
    LEVEL_NAMES,
    MAX_DAILY_EARN_PER_AGENT,
)

logger = logging.getLogger("apexjoule.ledger")


class AJLedger:
    """ApexJoule balance management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_balance(
        self, user_id: UUID, entity_id: Optional[str] = None
    ) -> ApexJouleBalance:
        """Get or create AJ balance for user/agent."""
        result = await self.db.execute(
            select(ApexJouleBalance).where(
                ApexJouleBalance.user_id == user_id,
                ApexJouleBalance.entity_id == entity_id,
            )
        )
        balance = result.scalar_one_or_none()

        if balance:
            return balance

        balance = ApexJouleBalance(user_id=user_id, entity_id=entity_id)
        self.db.add(balance)
        await self.db.flush()
        return balance

    async def credit(
        self,
        user_id: UUID,
        agent_id: str,
        agent_share: float,
        user_share: float,
        *,
        operation_type: str = "chat",
        tx_type: str = "earn",
        reason: Optional[str] = None,
        e_cost: Optional[float] = None,
        w_output: Optional[float] = None,
        kappa: Optional[float] = None,
        l_multiplier: Optional[float] = None,
        c_score: Optional[float] = None,
        d_score: Optional[float] = None,
        conversation_id: Optional[UUID] = None,
        message_id: Optional[UUID] = None,
        provider: Optional[str] = None,
        model_used: Optional[str] = None,
    ) -> Optional[ApexJouleTransaction]:
        """Credit AJ to agent and user, log transaction.

        Returns the transaction record, or None if daily cap exceeded.
        """
        # Check daily cap for agent
        if agent_share > 0:
            daily_earned = await self._daily_earned(user_id, agent_id)
            if daily_earned >= MAX_DAILY_EARN_PER_AGENT:
                logger.info(
                    f"AJ daily cap reached for {agent_id} "
                    f"(user={user_id}, earned={daily_earned})"
                )
                return None

            # Clamp to remaining daily allowance
            remaining = MAX_DAILY_EARN_PER_AGENT - daily_earned
            if agent_share > remaining:
                ratio = remaining / agent_share
                agent_share = remaining
                user_share = user_share * ratio

        total = agent_share + user_share
        if total <= 0:
            return None

        # Credit agent balance
        leveled_up = False
        agent_bal = None
        if agent_share > 0:
            agent_bal = await self.get_or_create_balance(user_id, agent_id)
            agent_bal.balance += Decimal(str(round(agent_share, 4)))
            agent_bal.total_earned += Decimal(str(round(agent_share, 4)))
            agent_bal.updated_at = datetime.utcnow()
            leveled_up = await self._check_level_up(agent_bal)

        # Credit user balance
        if user_share > 0:
            user_bal = await self.get_or_create_balance(user_id, None)
            user_bal.balance += Decimal(str(round(user_share, 4)))
            user_bal.total_earned += Decimal(str(round(user_share, 4)))
            user_bal.updated_at = datetime.utcnow()

        # Log transaction
        tx = ApexJouleTransaction(
            user_id=user_id,
            from_entity="system",
            to_entity=agent_id,
            amount=Decimal(str(round(total, 4))),
            tx_type=tx_type,
            reason=reason,
            e_cost=Decimal(str(round(e_cost, 4))) if e_cost is not None else None,
            w_output=Decimal(str(round(w_output, 4))) if w_output is not None else None,
            kappa=Decimal(str(round(kappa, 4))) if kappa is not None else None,
            l_multiplier=Decimal(str(round(l_multiplier, 4))) if l_multiplier is not None else None,
            c_score=Decimal(str(round(c_score, 3))) if c_score is not None else None,
            d_score=Decimal(str(round(d_score, 3))) if d_score is not None else None,
            conversation_id=conversation_id,
            message_id=message_id,
            operation_type=operation_type,
            provider=provider,
            model_used=model_used,
        )
        self.db.add(tx)
        await self.db.flush()

        logger.debug(
            f"AJ credit: {agent_id}={agent_share:.2f}, "
            f"user={user_share:.2f} ({operation_type})"
        )

        # Broadcast Village events (non-fatal)
        try:
            from app.services.village_events import get_village_broadcaster
            broadcaster = get_village_broadcaster()
            await broadcaster.broadcast_aj_earned(
                agent_id=agent_id or "USER",
                amount=total,
                new_balance=float(agent_bal.balance) if agent_bal else 0,
                l_multiplier=float(l_multiplier) if l_multiplier else 1.0,
            )
            if leveled_up and agent_bal:
                level_name = LEVEL_NAMES[min(agent_bal.level - 1, len(LEVEL_NAMES) - 1)]
                await broadcaster.broadcast_aj_level_up(
                    agent_id=agent_id,
                    new_level=agent_bal.level,
                    level_name=level_name,
                )
        except Exception as e:
            logger.warning(f"AJ village broadcast failed (non-fatal): {e}")

        return tx

    async def debit(
        self,
        user_id: UUID,
        entity_id: Optional[str],
        amount: float,
        *,
        tx_type: str = "spend",
        reason: Optional[str] = None,
    ) -> bool:
        """Debit AJ from an entity. Returns False if insufficient balance."""
        balance = await self.get_or_create_balance(user_id, entity_id)
        if float(balance.balance) < amount:
            return False

        balance.balance -= Decimal(str(round(amount, 4)))
        balance.total_spent += Decimal(str(round(amount, 4)))
        balance.updated_at = datetime.utcnow()

        tx = ApexJouleTransaction(
            user_id=user_id,
            from_entity=entity_id or "user",
            to_entity="system",
            amount=Decimal(str(round(amount, 4))),
            tx_type=tx_type,
            reason=reason,
        )
        self.db.add(tx)
        await self.db.flush()
        return True

    async def log_love_score(
        self,
        user_id: UUID,
        agent_id: str,
        c_score: float,
        d_score: float,
        *,
        interaction_type: Optional[str] = None,
        c_breakdown: Optional[dict] = None,
        d_breakdown: Optional[dict] = None,
        love_depth_before: Optional[float] = None,
        love_depth_after: Optional[float] = None,
    ) -> None:
        """Record a love score entry for audit trail."""
        entry = LoveScore(
            user_id=user_id,
            agent_id=agent_id,
            interaction_type=interaction_type,
            c_score=Decimal(str(round(c_score, 3))),
            d_score=Decimal(str(round(d_score, 3))),
            c_breakdown=c_breakdown,
            d_breakdown=d_breakdown,
            love_depth_before=Decimal(str(round(love_depth_before, 4))) if love_depth_before is not None else None,
            love_depth_after=Decimal(str(round(love_depth_after, 4))) if love_depth_after is not None else None,
        )
        self.db.add(entry)
        await self.db.flush()

    async def update_love_depth(
        self, user_id: UUID, agent_id: str, new_depth: float
    ) -> None:
        """Update agent's persistent Love Depth score."""
        bal = await self.get_or_create_balance(user_id, agent_id)
        bal.love_depth = Decimal(str(round(new_depth, 4)))
        bal.updated_at = datetime.utcnow()

    async def get_all_balances(self, user_id: UUID) -> list[ApexJouleBalance]:
        """Get all balances for a user (user + all agents)."""
        result = await self.db.execute(
            select(ApexJouleBalance)
            .where(ApexJouleBalance.user_id == user_id)
            .order_by(ApexJouleBalance.entity_id)
        )
        return list(result.scalars().all())

    async def get_transactions(
        self, user_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[ApexJouleTransaction]:
        """Get recent transactions for a user."""
        result = await self.db.execute(
            select(ApexJouleTransaction)
            .where(ApexJouleTransaction.user_id == user_id)
            .order_by(ApexJouleTransaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_economy_stats(self, user_id: UUID) -> dict:
        """Get economy overview stats for a user."""
        balances = await self.get_all_balances(user_id)

        total_balance = sum(float(b.balance) for b in balances)
        total_earned = sum(float(b.total_earned) for b in balances)
        total_spent = sum(float(b.total_spent) for b in balances)

        agents = {}
        user_balance = 0.0
        for b in balances:
            if b.entity_id:
                agents[b.entity_id] = {
                    "balance": float(b.balance),
                    "total_earned": float(b.total_earned),
                    "level": b.level,
                    "level_name": LEVEL_NAMES[min(b.level - 1, len(LEVEL_NAMES) - 1)],
                    "love_depth": float(b.love_depth),
                    "vitality": float(b.vitality),
                }
            else:
                user_balance = float(b.balance)

        return {
            "user_balance": user_balance,
            "agents": agents,
            "total_balance": total_balance,
            "total_earned": total_earned,
            "total_spent": total_spent,
        }

    async def _daily_earned(self, user_id: UUID, agent_id: str) -> float:
        """Get total AJ earned by an agent today."""
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await self.db.execute(
            select(func.coalesce(func.sum(ApexJouleTransaction.amount), 0))
            .where(
                ApexJouleTransaction.user_id == user_id,
                ApexJouleTransaction.to_entity == agent_id,
                ApexJouleTransaction.tx_type == "earn",
                ApexJouleTransaction.created_at >= today_start,
            )
        )
        return float(result.scalar() or 0)

    async def _check_level_up(self, balance: ApexJouleBalance) -> bool:
        """Check and apply level-up based on total_earned."""
        earned = float(balance.total_earned)
        new_level = 1
        for i, threshold in enumerate(LEVEL_THRESHOLDS):
            if earned >= threshold:
                new_level = i + 1

        if new_level > balance.level:
            old_level = balance.level
            balance.level = new_level
            logger.info(
                f"AJ level-up: {balance.entity_id} "
                f"{old_level} -> {new_level} "
                f"({LEVEL_NAMES[new_level - 1]})"
            )
            return True
        return False
