"""
Marketplace API — Browse, list, purchase, and rate agent bundles.

Endpoints:
- GET    /marketplace/listings       — Browse active listings
- GET    /marketplace/listings/{id}  — Get listing details
- POST   /marketplace/listings       — Create a new listing
- POST   /marketplace/purchase/{id}  — Purchase/download a listing
- POST   /marketplace/rate/{id}      — Rate a purchased listing
- DELETE /marketplace/listings/{id}  — Delist your own listing
"""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.marketplace import MarketplaceListing, MarketplacePurchase
from app.auth.deps import get_current_user
from app.services.portability.importer import AgentImporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEMAS
# ═══════════════════════════════════════════════════════════════════════════════

class CreateListingRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    bundle: dict = Field(..., description="The exported agent bundle")
    price_aj: float = Field(default=0, ge=0, le=100000)
    tags: list[str] = Field(default_factory=list, max_length=10)


class RateRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)


# ═══════════════════════════════════════════════════════════════════════════════
# BROWSE
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/listings")
async def browse_listings(
    search: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
    sort: str = Query(default="newest", regex="^(newest|popular|cheapest|top_rated)$"),
    limit: int = Query(default=20, le=50),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse marketplace listings. No auth required."""
    query = (
        select(MarketplaceListing)
        .where(MarketplaceListing.status == "active")
    )

    if search:
        query = query.where(MarketplaceListing.title.ilike(f"%{search}%"))

    if tag:
        query = query.where(MarketplaceListing.tags.contains([tag]))

    # Sorting
    if sort == "newest":
        query = query.order_by(desc(MarketplaceListing.created_at))
    elif sort == "popular":
        query = query.order_by(desc(MarketplaceListing.downloads))
    elif sort == "cheapest":
        query = query.order_by(MarketplaceListing.price_aj)
    elif sort == "top_rated":
        query = query.order_by(desc(MarketplaceListing.rating_sum))

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    listings = result.scalars().all()

    # Count total
    count_query = (
        select(func.count(MarketplaceListing.id))
        .where(MarketplaceListing.status == "active")
    )
    if search:
        count_query = count_query.where(MarketplaceListing.title.ilike(f"%{search}%"))
    if tag:
        count_query = count_query.where(MarketplaceListing.tags.contains([tag]))
    total = (await db.execute(count_query)).scalar() or 0

    return {
        "listings": [
            {
                "id": str(l.id),
                "title": l.title,
                "description": l.description,
                "agent_id": l.agent_id,
                "price_aj": float(l.price_aj),
                "downloads": l.downloads,
                "rating": round(l.rating_sum / l.rating_count, 1) if l.rating_count > 0 else None,
                "rating_count": l.rating_count,
                "tags": l.tags or [],
                "stats": l.bundle.get("stats", {}),
                "created_at": l.created_at.isoformat(),
            }
            for l in listings
        ],
        "total": total,
    }


@router.get("/listings/{listing_id}")
async def get_listing(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get full listing details (excludes bundle data until purchased)."""
    listing = await db.get(MarketplaceListing, listing_id)
    if not listing or listing.status != "active":
        raise HTTPException(status_code=404, detail="Listing not found")

    return {
        "id": str(listing.id),
        "title": listing.title,
        "description": listing.description,
        "agent_id": listing.agent_id,
        "price_aj": float(listing.price_aj),
        "downloads": listing.downloads,
        "rating": round(listing.rating_sum / listing.rating_count, 1) if listing.rating_count > 0 else None,
        "rating_count": listing.rating_count,
        "tags": listing.tags or [],
        "stats": listing.bundle.get("stats", {}),
        "created_at": listing.created_at.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CREATE LISTING
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/listings")
async def create_listing(
    request: CreateListingRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List an agent bundle on the marketplace."""
    # Validate bundle
    errors = AgentImporter.validate_bundle(request.bundle)
    if errors:
        raise HTTPException(status_code=400, detail={"errors": errors})

    agent_id = request.bundle.get("agent", {}).get("id", "unknown")

    listing = MarketplaceListing(
        seller_id=user.id,
        title=request.title,
        description=request.description,
        agent_id=agent_id,
        bundle=request.bundle,
        price_aj=Decimal(str(request.price_aj)),
        tags=request.tags[:10],
    )
    db.add(listing)
    await db.commit()
    await db.refresh(listing)

    logger.info(f"User {user.id} listed agent {agent_id} for {request.price_aj} AJ")

    return {
        "success": True,
        "listing_id": str(listing.id),
        "message": f"'{request.title}' is now live on the marketplace!",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# PURCHASE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/purchase/{listing_id}")
async def purchase_listing(
    listing_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Purchase a listing and import the bundle."""
    listing = await db.get(MarketplaceListing, listing_id)
    if not listing or listing.status != "active":
        raise HTTPException(status_code=404, detail="Listing not found")

    # Check if already purchased
    existing = await db.execute(
        select(MarketplacePurchase)
        .where(MarketplacePurchase.listing_id == listing_id)
        .where(MarketplacePurchase.buyer_id == user.id)
    )
    if existing.scalar_one_or_none():
        # Already purchased — just return the bundle for re-download
        return {
            "success": True,
            "message": "You already own this bundle. Re-downloading.",
            "bundle": listing.bundle,
            "already_owned": True,
        }

    # Deduct AJ if not free
    if listing.price_aj > 0:
        from app.services.apexjoule.ledger import AJLedger
        ledger = AJLedger(db)
        balance = await ledger.get_balance(user.id)
        if not balance or balance.balance < listing.price_aj:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient AJ balance. Need {listing.price_aj} AJ.",
            )
        # Debit buyer
        await ledger.debit(
            user_id=user.id,
            entity_type="user",
            amount=float(listing.price_aj),
            tx_type="marketplace_purchase",
            description=f"Marketplace: {listing.title}",
        )
        # Credit seller
        await ledger.credit(
            user_id=listing.seller_id,
            entity_type="user",
            amount=float(listing.price_aj * Decimal("0.85")),  # 85% to seller, 15% platform fee
            tx_type="marketplace_sale",
            description=f"Marketplace sale: {listing.title}",
        )

    # Record purchase
    purchase = MarketplacePurchase(
        listing_id=listing_id,
        buyer_id=user.id,
        price_aj=listing.price_aj,
    )
    db.add(purchase)

    # Increment download count
    listing.downloads += 1

    await db.commit()

    logger.info(f"User {user.id} purchased listing {listing_id} for {listing.price_aj} AJ")

    return {
        "success": True,
        "message": f"Purchased '{listing.title}'! Use Import to add to your space.",
        "bundle": listing.bundle,
        "price_paid": float(listing.price_aj),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# RATE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/rate/{listing_id}")
async def rate_listing(
    listing_id: UUID,
    request: RateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rate a purchased listing (1-5 stars)."""
    # Must have purchased
    result = await db.execute(
        select(MarketplacePurchase)
        .where(MarketplacePurchase.listing_id == listing_id)
        .where(MarketplacePurchase.buyer_id == user.id)
    )
    purchase = result.scalar_one_or_none()
    if not purchase:
        raise HTTPException(status_code=403, detail="You must purchase this listing before rating it")

    listing = await db.get(MarketplaceListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    # Update rating (remove old if re-rating)
    if purchase.rating:
        listing.rating_sum -= purchase.rating
        listing.rating_count -= 1

    purchase.rating = request.rating
    listing.rating_sum += request.rating
    listing.rating_count += 1

    await db.commit()

    avg = round(listing.rating_sum / listing.rating_count, 1) if listing.rating_count > 0 else None
    return {"success": True, "new_rating": avg, "rating_count": listing.rating_count}


# ═══════════════════════════════════════════════════════════════════════════════
# DELIST
# ═══════════════════════════════════════════════════════════════════════════════

@router.delete("/listings/{listing_id}")
async def delist_listing(
    listing_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delist your own listing from the marketplace."""
    listing = await db.get(MarketplaceListing, listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.seller_id != user.id:
        raise HTTPException(status_code=403, detail="You can only delist your own listings")

    listing.status = "delisted"
    await db.commit()

    return {"success": True, "message": "Listing removed from marketplace"}
