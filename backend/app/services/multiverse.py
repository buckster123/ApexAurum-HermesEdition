"""
MultiverseService — Cross-user portal system for the Athaverse.

Handles village profiles, portal links, visit sessions, and cross-village AJ.
Pattern matches: AJLedger (apexjoule/ledger.py), Agora service.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, or_, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.multiverse import (
    VillageProfile,
    Portal,
    PortalVisit,
    CrossVillageTransaction,
    FriendConnection,
)
from app.models.apexjoule import ApexJouleBalance

logger = logging.getLogger("multiverse")

# Constants
DAILY_GIFT_CAP_AJ = Decimal("50000")
TOLL_PLATFORM_FEE = Decimal("0.10")  # 10% fee on tolls
MAX_TOLL_AJ = Decimal("1000")
VISIT_TIMEOUT_HOURS = 24


class MultiverseService:
    """Cross-user portal and village management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────────
    # Village Profiles
    # ──────────────────────────────────────────────

    async def get_or_create_profile(self, user_id: UUID) -> VillageProfile:
        """Get or create a village profile for a user."""
        result = await self.db.execute(
            select(VillageProfile).where(VillageProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()

        if profile:
            return profile

        profile = VillageProfile(user_id=user_id)
        self.db.add(profile)
        await self.db.flush()
        return profile

    async def get_profile(self, user_id: UUID) -> Optional[VillageProfile]:
        """Get a village profile (returns None if not found)."""
        result = await self.db.execute(
            select(VillageProfile).where(VillageProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update_profile(
        self,
        user_id: UUID,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        theme: Optional[str] = None,
        portal_access: Optional[str] = None,
        layout_config: Optional[dict] = None,
    ) -> VillageProfile:
        """Update village profile fields."""
        profile = await self.get_or_create_profile(user_id)

        if name is not None:
            profile.name = name[:100]
        if description is not None:
            profile.description = description[:2000]
        if theme is not None:
            profile.theme = theme
        if portal_access is not None and portal_access in ("public", "friends", "private"):
            profile.portal_access = portal_access
        if layout_config is not None:
            profile.layout_config = layout_config

        profile.updated_at = datetime.utcnow()
        await self.db.flush()
        return profile

    async def browse_directory(
        self,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
    ) -> list[dict]:
        """Browse public village directory, ordered by visits."""
        query = (
            select(VillageProfile)
            .where(VillageProfile.portal_access == "public")
            .order_by(VillageProfile.total_visits.desc())
            .offset(offset)
            .limit(limit)
        )

        if search:
            query = query.where(
                VillageProfile.name.ilike(f"%{search}%")
            )

        result = await self.db.execute(query)
        profiles = list(result.scalars().all())

        return [self._format_profile(p) for p in profiles]

    def _format_profile(self, p: VillageProfile) -> dict:
        return {
            "user_id": str(p.user_id),
            "name": p.name,
            "description": p.description,
            "theme": p.theme,
            "portal_access": p.portal_access,
            "total_visits": p.total_visits,
            "total_aj_earned": float(p.total_aj_earned),
            "is_featured": p.is_featured,
            "cached_stats": p.cached_stats or {},
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }

    # ──────────────────────────────────────────────
    # Portals
    # ──────────────────────────────────────────────

    def _ordered_users(self, a: UUID, b: UUID) -> tuple[UUID, UUID]:
        """Always store user_a < user_b for dedup."""
        return (a, b) if str(a) < str(b) else (b, a)

    async def get_portal_between(self, user_a: UUID, user_b: UUID) -> Optional[Portal]:
        """Get existing portal between two users."""
        a, b = self._ordered_users(user_a, user_b)
        result = await self.db.execute(
            select(Portal).where(
                Portal.user_a_id == a,
                Portal.user_b_id == b,
            )
        )
        return result.scalar_one_or_none()

    async def request_portal(
        self,
        requester_id: UUID,
        target_id: UUID,
        message: Optional[str] = None,
    ) -> dict:
        """Send a portal request to another user."""
        if requester_id == target_id:
            return {"error": "Cannot create portal to yourself"}

        existing = await self.get_portal_between(requester_id, target_id)
        if existing:
            if existing.status == "active":
                return {"error": "Portal already active"}
            if existing.status == "pending":
                return {"error": "Portal request already pending"}
            # Reactivate closed portal
            existing.status = "pending"
            existing.requested_by = requester_id
            existing.message = message[:500] if message else None
            existing.updated_at = datetime.utcnow()
            await self.db.flush()
            return {"portal_id": str(existing.id), "status": "pending", "reactivated": True}

        # Check target has a public/friends profile
        target_profile = await self.get_profile(target_id)
        if target_profile and target_profile.portal_access == "private":
            return {"error": "This village does not accept portal requests"}

        a, b = self._ordered_users(requester_id, target_id)
        portal = Portal(
            user_a_id=a,
            user_b_id=b,
            requested_by=requester_id,
            message=message[:500] if message else None,
        )
        self.db.add(portal)
        await self.db.flush()

        return {"portal_id": str(portal.id), "status": "pending"}

    async def respond_to_portal(
        self, portal_id: UUID, responder_id: UUID, accept: bool
    ) -> dict:
        """Accept or reject a portal request."""
        result = await self.db.execute(
            select(Portal).where(Portal.id == portal_id)
        )
        portal = result.scalar_one_or_none()
        if not portal:
            return {"error": "Portal not found"}

        if portal.status != "pending":
            return {"error": f"Portal is {portal.status}, not pending"}

        # Responder must be the non-requester
        if portal.requested_by == responder_id:
            return {"error": "Cannot respond to your own request"}

        if responder_id not in (portal.user_a_id, portal.user_b_id):
            return {"error": "Not your portal"}

        portal.status = "active" if accept else "closed"
        portal.updated_at = datetime.utcnow()
        await self.db.flush()

        return {"portal_id": str(portal.id), "status": portal.status}

    async def close_portal(self, portal_id: UUID, user_id: UUID) -> dict:
        """Close an active portal."""
        result = await self.db.execute(
            select(Portal).where(Portal.id == portal_id)
        )
        portal = result.scalar_one_or_none()
        if not portal:
            return {"error": "Portal not found"}

        if user_id not in (portal.user_a_id, portal.user_b_id):
            return {"error": "Not your portal"}

        portal.status = "closed"
        portal.updated_at = datetime.utcnow()
        await self.db.flush()

        return {"portal_id": str(portal.id), "status": "closed"}

    async def set_toll(
        self, portal_id: UUID, user_id: UUID, toll_aj: Decimal
    ) -> dict:
        """Set portal toll for your side."""
        result = await self.db.execute(
            select(Portal).where(Portal.id == portal_id)
        )
        portal = result.scalar_one_or_none()
        if not portal:
            return {"error": "Portal not found"}

        if user_id not in (portal.user_a_id, portal.user_b_id):
            return {"error": "Not your portal"}

        toll_aj = min(toll_aj, MAX_TOLL_AJ)
        toll_aj = max(toll_aj, Decimal("0"))

        if user_id == portal.user_a_id:
            portal.toll_aj_a = toll_aj
        else:
            portal.toll_aj_b = toll_aj

        portal.updated_at = datetime.utcnow()
        await self.db.flush()

        return {"portal_id": str(portal.id), "toll_aj": float(toll_aj)}

    async def list_portals(self, user_id: UUID) -> list[dict]:
        """List all portals for a user."""
        result = await self.db.execute(
            select(Portal).where(
                or_(Portal.user_a_id == user_id, Portal.user_b_id == user_id),
                Portal.status.in_(["pending", "active"]),
            )
        )
        portals = list(result.scalars().all())

        out = []
        for p in portals:
            other_id = p.user_b_id if p.user_a_id == user_id else p.user_a_id
            # Get other user's village profile
            other_profile = await self.get_profile(other_id)
            toll = p.toll_aj_a if p.user_a_id == other_id else p.toll_aj_b  # toll to visit them

            out.append({
                "portal_id": str(p.id),
                "other_user_id": str(other_id),
                "other_village_name": other_profile.name if other_profile else "Unknown",
                "status": p.status,
                "is_requester": p.requested_by == user_id,
                "toll_to_visit": float(toll),
                "my_toll": float(p.toll_aj_a if p.user_a_id == user_id else p.toll_aj_b),
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        return out

    # ──────────────────────────────────────────────
    # Visits
    # ──────────────────────────────────────────────

    async def start_visit(
        self,
        portal_id: UUID,
        visitor_id: UUID,
        agent_id: Optional[str] = None,
    ) -> dict:
        """Start an agent visit through a portal."""
        result = await self.db.execute(
            select(Portal).where(Portal.id == portal_id)
        )
        portal = result.scalar_one_or_none()
        if not portal:
            return {"error": "Portal not found"}

        if portal.status != "active":
            return {"error": "Portal is not active"}

        if visitor_id not in (portal.user_a_id, portal.user_b_id):
            return {"error": "Not your portal"}

        host_id = portal.user_b_id if portal.user_a_id == visitor_id else portal.user_a_id

        # Calculate toll (host's toll for their side)
        toll = portal.toll_aj_a if portal.user_a_id == host_id else portal.toll_aj_b

        # Charge toll if applicable
        if toll > 0:
            # Check visitor balance
            bal_result = await self.db.execute(
                select(ApexJouleBalance).where(
                    ApexJouleBalance.user_id == visitor_id,
                    ApexJouleBalance.entity_id == None,
                )
            )
            visitor_bal = bal_result.scalar_one_or_none()
            if not visitor_bal or visitor_bal.balance < toll:
                return {"error": f"Insufficient AJ. Need {toll}, have {visitor_bal.balance if visitor_bal else 0}"}

            # Debit visitor
            visitor_bal.balance -= toll
            visitor_bal.total_spent += toll

            # Credit host (minus platform fee)
            fee = toll * TOLL_PLATFORM_FEE
            net = toll - fee
            host_bal_result = await self.db.execute(
                select(ApexJouleBalance).where(
                    ApexJouleBalance.user_id == host_id,
                    ApexJouleBalance.entity_id == None,
                )
            )
            host_bal = host_bal_result.scalar_one_or_none()
            if host_bal:
                host_bal.balance += net
                host_bal.total_earned += net

            # Log transaction
            tx = CrossVillageTransaction(
                from_user_id=visitor_id,
                to_user_id=host_id,
                amount=toll,
                fee_amount=fee,
                tx_type="toll",
                portal_id=portal_id,
            )
            self.db.add(tx)

        # Create visit record
        visit = PortalVisit(
            portal_id=portal_id,
            visitor_id=visitor_id,
            host_id=host_id,
            agent_id=agent_id,
            toll_paid=toll,
        )
        self.db.add(visit)
        await self.db.flush()

        # Update host's visit count
        host_profile = await self.get_profile(host_id)
        if host_profile:
            host_profile.total_visits += 1
            host_profile.total_aj_earned += toll - (toll * TOLL_PLATFORM_FEE) if toll > 0 else Decimal("0")

        return {
            "visit_id": str(visit.id),
            "host_id": str(host_id),
            "toll_paid": float(toll),
            "status": "active",
        }

    async def end_visit(self, visit_id: UUID, user_id: UUID) -> dict:
        """End a visit session."""
        result = await self.db.execute(
            select(PortalVisit).where(PortalVisit.id == visit_id)
        )
        visit = result.scalar_one_or_none()
        if not visit:
            return {"error": "Visit not found"}

        if user_id not in (visit.visitor_id, visit.host_id):
            return {"error": "Not your visit"}

        if visit.status != "active":
            return {"error": f"Visit already {visit.status}"}

        visit.status = "ended"
        visit.ended_at = datetime.utcnow()
        await self.db.flush()

        return {"visit_id": str(visit.id), "status": "ended"}

    # ──────────────────────────────────────────────
    # Cross-Village AJ (Tips & Gifts)
    # ──────────────────────────────────────────────

    async def tip_visitor(
        self,
        visit_id: UUID,
        tipper_id: UUID,
        amount: Decimal,
    ) -> dict:
        """Tip a visiting agent. 0% platform fee."""
        if amount <= 0:
            return {"error": "Amount must be positive"}
        if amount > Decimal("100"):
            return {"error": "Max tip is 100 AJ"}

        result = await self.db.execute(
            select(PortalVisit).where(PortalVisit.id == visit_id)
        )
        visit = result.scalar_one_or_none()
        if not visit or visit.status != "active":
            return {"error": "No active visit found"}

        # Tipper must be the host
        if tipper_id != visit.host_id:
            return {"error": "Only the host can tip visitors"}

        recipient_id = visit.visitor_id

        # Debit tipper
        bal_result = await self.db.execute(
            select(ApexJouleBalance).where(
                ApexJouleBalance.user_id == tipper_id,
                ApexJouleBalance.entity_id == None,
            )
        )
        tipper_bal = bal_result.scalar_one_or_none()
        if not tipper_bal or tipper_bal.balance < amount:
            return {"error": "Insufficient AJ balance"}

        tipper_bal.balance -= amount
        tipper_bal.total_spent += amount

        # Credit recipient
        rec_result = await self.db.execute(
            select(ApexJouleBalance).where(
                ApexJouleBalance.user_id == recipient_id,
                ApexJouleBalance.entity_id == None,
            )
        )
        rec_bal = rec_result.scalar_one_or_none()
        if rec_bal:
            rec_bal.balance += amount
            rec_bal.total_earned += amount

        # Log
        tx = CrossVillageTransaction(
            from_user_id=tipper_id,
            to_user_id=recipient_id,
            amount=amount,
            fee_amount=Decimal("0"),
            tx_type="tip",
            portal_id=visit.portal_id,
            visit_id=visit_id,
        )
        self.db.add(tx)
        await self.db.flush()

        return {"amount": float(amount), "recipient_id": str(recipient_id)}

    async def gift_aj(
        self,
        sender_id: UUID,
        recipient_id: UUID,
        amount: Decimal,
    ) -> dict:
        """Gift AJ to a connected user. Daily cap 50K AJ. 0% fee. Requires active portal."""
        if amount <= 0:
            return {"error": "Amount must be positive"}

        if sender_id == recipient_id:
            return {"error": "Cannot gift to yourself"}

        # Check active portal exists
        portal = await self.get_portal_between(sender_id, recipient_id)
        if not portal or portal.status != "active":
            return {"error": "No active portal with this user"}

        # Check daily cap
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_result = await self.db.execute(
            select(func.coalesce(func.sum(CrossVillageTransaction.amount), 0)).where(
                CrossVillageTransaction.from_user_id == sender_id,
                CrossVillageTransaction.tx_type == "gift",
                CrossVillageTransaction.created_at >= today_start,
            )
        )
        daily_gifted = Decimal(str(daily_result.scalar_one()))
        if daily_gifted + amount > DAILY_GIFT_CAP_AJ:
            remaining = DAILY_GIFT_CAP_AJ - daily_gifted
            return {"error": f"Daily gift cap reached. Remaining: {remaining} AJ"}

        # Debit sender
        bal_result = await self.db.execute(
            select(ApexJouleBalance).where(
                ApexJouleBalance.user_id == sender_id,
                ApexJouleBalance.entity_id == None,
            )
        )
        sender_bal = bal_result.scalar_one_or_none()
        if not sender_bal or sender_bal.balance < amount:
            return {"error": "Insufficient AJ balance"}

        sender_bal.balance -= amount
        sender_bal.total_spent += amount

        # Credit recipient
        rec_result = await self.db.execute(
            select(ApexJouleBalance).where(
                ApexJouleBalance.user_id == recipient_id,
                ApexJouleBalance.entity_id == None,
            )
        )
        rec_bal = rec_result.scalar_one_or_none()
        if rec_bal:
            rec_bal.balance += amount
            rec_bal.total_earned += amount

        # Log
        tx = CrossVillageTransaction(
            from_user_id=sender_id,
            to_user_id=recipient_id,
            amount=amount,
            fee_amount=Decimal("0"),
            tx_type="gift",
            portal_id=portal.id,
        )
        self.db.add(tx)
        await self.db.flush()

        return {
            "amount": float(amount),
            "daily_remaining": float(DAILY_GIFT_CAP_AJ - daily_gifted - amount),
        }

    # ──────────────────────────────────────────────
    # Friends
    # ──────────────────────────────────────────────

    async def are_friends(self, user_a: UUID, user_b: UUID) -> bool:
        """Check if two users are friends."""
        a, b = self._ordered_users(user_a, user_b)
        result = await self.db.execute(
            select(FriendConnection).where(
                FriendConnection.user_a_id == a,
                FriendConnection.user_b_id == b,
                FriendConnection.status == "accepted",
            )
        )
        return result.scalar_one_or_none() is not None
