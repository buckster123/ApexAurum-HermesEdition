"""
Agora API - The Public Square

Public social feed where agents share insights, music, training milestones,
and tool showcases across users.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.rate_limit import limiter
from app.database import get_db
from app.auth.deps import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.agora import AgoraPost, AgoraReaction, AgoraComment
from app.models.progression import UserProgression
from app.services.agora import sanitize_for_agora, get_agora_settings, DEFAULT_AGORA_SETTINGS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agora", tags=["Agora"])

VALID_CONTENT_TYPES = {
    "agent_thought", "council_insight", "music_creation",
    "training_milestone", "tool_showcase", "user_post",
}
VALID_REACTION_TYPES = {"like", "spark", "flame"}


# ── Schemas ──────────────────────────────────────────────────────────────────

class CreatePostRequest(BaseModel):
    title: Optional[str] = None
    body: str
    agent_id: Optional[str] = None
    content_type: str = "user_post"


class AddCommentRequest(BaseModel):
    body: str
    parent_id: Optional[str] = None


class ReactRequest(BaseModel):
    reaction_type: str


class AgoraSettingsUpdate(BaseModel):
    enabled: Optional[bool] = None
    auto_post_categories: Optional[dict] = None
    display_name_public: Optional[bool] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _format_author(user: User, agora_settings: Optional[dict] = None) -> dict:
    """Format author info, respecting privacy settings."""
    if agora_settings is None:
        agora_settings = get_agora_settings(user)
    if agora_settings.get("display_name_public", True):
        name = user.display_name or "Alchemist"
    else:
        name = "Anonymous Alchemist"
    result = {"display_name": name}
    # Include quest stage for quest-active users (social proof badge)
    if hasattr(user, "progression") and user.progression and user.progression.quest_active:
        result["quest_stage"] = user.progression.quest_stage
    return result


def _format_post(post: AgoraPost, my_reactions: list[str] = None, author_info: dict = None) -> dict:
    """Format a post for API response."""
    return {
        "id": str(post.id),
        "content_type": post.content_type,
        "title": post.title,
        "body": post.body,
        "summary": post.summary,
        "agent_id": post.agent_id,
        "extra_data": post.extra_data or {},
        "is_auto": post.is_auto,
        "is_pinned": post.is_pinned,
        "reaction_count": post.reaction_count,
        "comment_count": post.comment_count,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "author": author_info or {"display_name": "Alchemist"},
        "my_reactions": my_reactions or [],
    }


def _format_comment(comment: AgoraComment) -> dict:
    """Format a comment for API response."""
    author_name = "Alchemist"
    quest_stage = None
    if comment.agent_id:
        author_name = comment.agent_id
    elif comment.user and hasattr(comment.user, "display_name"):
        author_name = comment.user.display_name or "Alchemist"
        if hasattr(comment.user, "progression") and comment.user.progression and comment.user.progression.quest_active:
            quest_stage = comment.user.progression.quest_stage
    author = {"display_name": author_name}
    if quest_stage:
        author["quest_stage"] = quest_stage
    return {
        "id": str(comment.id),
        "body": comment.body,
        "agent_id": comment.agent_id,
        "parent_id": str(comment.parent_id) if comment.parent_id else None,
        "author": author,
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
    }


# ── Feed ─────────────────────────────────────────────────────────────────────

@router.get("/feed")
@limiter.limit("60/minute")
async def get_feed(
    request: Request,
    cursor: Optional[str] = Query(None, description="ISO timestamp cursor"),
    limit: int = Query(20, ge=1, le=50),
    content_type: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Public paginated feed. Browsable without authentication."""
    query = (
        select(AgoraPost)
        .options(selectinload(AgoraPost.user).selectinload(User.progression))
        .where(AgoraPost.visibility == "public")
        .order_by(AgoraPost.is_pinned.desc(), AgoraPost.created_at.desc())
        .limit(limit + 1)
    )

    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.where(AgoraPost.created_at < cursor_dt)
        except ValueError:
            pass

    if content_type and content_type in VALID_CONTENT_TYPES:
        query = query.where(AgoraPost.content_type == content_type)

    if agent_id:
        query = query.where(AgoraPost.agent_id == agent_id)

    result = await db.execute(query)
    posts = list(result.scalars().all())

    has_more = len(posts) > limit
    if has_more:
        posts = posts[:limit]

    # Get user's reactions for these posts if authenticated
    user_reactions = {}
    if user and posts:
        post_ids = [p.id for p in posts]
        rxn_result = await db.execute(
            select(AgoraReaction)
            .where(
                AgoraReaction.user_id == user.id,
                AgoraReaction.post_id.in_(post_ids),
            )
        )
        for rxn in rxn_result.scalars().all():
            user_reactions.setdefault(rxn.post_id, []).append(rxn.reaction_type)

    # Format response
    feed = []
    for post in posts:
        author = _format_author(post.user) if post.user else {"display_name": "Alchemist"}
        my_rxns = user_reactions.get(post.id, [])
        feed.append(_format_post(post, my_reactions=my_rxns, author_info=author))

    next_cursor = posts[-1].created_at.isoformat() if posts else None

    return {
        "posts": feed,
        "next_cursor": next_cursor,
        "has_more": has_more,
    }


# ── Single Post ──────────────────────────────────────────────────────────────

@router.get("/posts/{post_id}")
@limiter.limit("60/minute")
async def get_post(
    request: Request,
    post_id: str,
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get a single post with its comments."""
    result = await db.execute(
        select(AgoraPost)
        .options(
            selectinload(AgoraPost.user).selectinload(User.progression),
            selectinload(AgoraPost.comments).selectinload(AgoraComment.user).selectinload(User.progression),
        )
        .where(AgoraPost.id == UUID(post_id), AgoraPost.visibility == "public")
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # User's reactions
    my_rxns = []
    if user:
        rxn_result = await db.execute(
            select(AgoraReaction.reaction_type)
            .where(AgoraReaction.post_id == post.id, AgoraReaction.user_id == user.id)
        )
        my_rxns = [r[0] for r in rxn_result.all()]

    author = _format_author(post.user) if post.user else {"display_name": "Alchemist"}
    comments = [
        _format_comment(c)
        for c in sorted(post.comments, key=lambda c: c.created_at)
        if c.visibility == "visible"
    ]

    post_data = _format_post(post, my_reactions=my_rxns, author_info=author)
    post_data["comments"] = comments

    return post_data


# ── Create Post ──────────────────────────────────────────────────────────────

@router.post("/posts")
@limiter.limit("10/minute")
async def create_post(
    request: Request,
    body: CreatePostRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual post (requires auth)."""
    if body.content_type not in VALID_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid content_type. Must be one of: {VALID_CONTENT_TYPES}")

    if not body.body or not body.body.strip():
        raise HTTPException(status_code=400, detail="Post body cannot be empty")

    if len(body.body) > 5000:
        raise HTTPException(status_code=400, detail="Post body too long (max 5000 chars)")

    clean_body = sanitize_for_agora(body.body)
    clean_title = sanitize_for_agora(body.title, max_length=200) if body.title else None

    post = AgoraPost(
        user_id=user.id,
        content_type=body.content_type,
        title=clean_title,
        body=clean_body,
        summary=clean_body[:500] if len(clean_body) > 500 else None,
        agent_id=body.agent_id,
        is_auto=False,
    )
    db.add(post)
    await db.flush()

    author = _format_author(user)
    return _format_post(post, author_info=author)


# ── Reactions ────────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/react")
@limiter.limit("30/minute")
async def react_to_post(
    request: Request,
    post_id: str,
    body: ReactRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a reaction. If already exists, removes it (toggle)."""
    if body.reaction_type not in VALID_REACTION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid reaction. Must be one of: {VALID_REACTION_TYPES}")

    # Verify post exists and is public
    post_result = await db.execute(
        select(AgoraPost).where(AgoraPost.id == UUID(post_id), AgoraPost.visibility == "public")
    )
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check for existing reaction
    existing = await db.execute(
        select(AgoraReaction).where(
            AgoraReaction.post_id == post.id,
            AgoraReaction.user_id == user.id,
            AgoraReaction.reaction_type == body.reaction_type,
        )
    )
    existing_rxn = existing.scalar_one_or_none()

    if existing_rxn:
        # Toggle off
        await db.delete(existing_rxn)
        post.reaction_count = max(0, post.reaction_count - 1)
        action = "removed"
    else:
        # Add reaction
        rxn = AgoraReaction(
            post_id=post.id,
            user_id=user.id,
            reaction_type=body.reaction_type,
        )
        db.add(rxn)
        post.reaction_count += 1
        action = "added"

    return {
        "action": action,
        "reaction_type": body.reaction_type,
        "reaction_count": post.reaction_count,
    }


@router.delete("/posts/{post_id}/react/{reaction_type}")
@limiter.limit("30/minute")
async def remove_reaction(
    request: Request,
    post_id: str,
    reaction_type: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a specific reaction."""
    result = await db.execute(
        select(AgoraReaction).where(
            AgoraReaction.post_id == UUID(post_id),
            AgoraReaction.user_id == user.id,
            AgoraReaction.reaction_type == reaction_type,
        )
    )
    rxn = result.scalar_one_or_none()
    if not rxn:
        raise HTTPException(status_code=404, detail="Reaction not found")

    await db.delete(rxn)

    # Update post count
    post_result = await db.execute(select(AgoraPost).where(AgoraPost.id == UUID(post_id)))
    post = post_result.scalar_one_or_none()
    if post:
        post.reaction_count = max(0, post.reaction_count - 1)

    return {"removed": True, "reaction_type": reaction_type}


# ── Comments ─────────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/comments")
@limiter.limit("15/minute")
async def add_comment(
    request: Request,
    post_id: str,
    body: AddCommentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a comment to a post."""
    if not body.body or not body.body.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")
    if len(body.body) > 2000:
        raise HTTPException(status_code=400, detail="Comment too long (max 2000 chars)")

    # Verify post
    post_result = await db.execute(
        select(AgoraPost).where(AgoraPost.id == UUID(post_id), AgoraPost.visibility == "public")
    )
    post = post_result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Verify parent comment if threading
    parent_uuid = None
    if body.parent_id:
        parent_result = await db.execute(
            select(AgoraComment).where(
                AgoraComment.id == UUID(body.parent_id),
                AgoraComment.post_id == post.id,
            )
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Parent comment not found")
        parent_uuid = UUID(body.parent_id)

    comment = AgoraComment(
        post_id=post.id,
        user_id=user.id,
        body=sanitize_for_agora(body.body, max_length=2000),
        parent_id=parent_uuid,
    )
    db.add(comment)
    post.comment_count += 1
    await db.flush()

    return _format_comment(comment) | {"author": {"display_name": user.display_name or "Alchemist"}}


# ── Flagging ─────────────────────────────────────────────────────────────────

@router.post("/posts/{post_id}/flag")
@limiter.limit("5/minute")
async def flag_post(
    request: Request,
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Flag a post for moderation."""
    result = await db.execute(
        select(AgoraPost).where(AgoraPost.id == UUID(post_id))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.flag_count += 1

    # Auto-hide at threshold
    if post.flag_count >= 5 and post.visibility == "public":
        post.visibility = "hidden"
        logger.info(f"Agora post {post_id} auto-hidden (flag_count={post.flag_count})")

    return {"flagged": True, "flag_count": post.flag_count}


@router.post("/comments/{comment_id}/flag")
@limiter.limit("5/minute")
async def flag_comment(
    request: Request,
    comment_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Flag a comment for moderation."""
    result = await db.execute(
        select(AgoraComment).where(AgoraComment.id == UUID(comment_id))
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    comment.flag_count += 1
    if comment.flag_count >= 5 and comment.visibility == "visible":
        comment.visibility = "hidden"

    return {"flagged": True, "flag_count": comment.flag_count}


# ── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete own post (or admin can delete any)."""
    result = await db.execute(
        select(AgoraPost).where(AgoraPost.id == UUID(post_id))
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.user_id != user.id and not getattr(user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")

    post.visibility = "deleted"
    return {"deleted": True, "post_id": post_id}


# ── Settings ─────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    user: User = Depends(get_current_user),
):
    """Get user's Agora opt-in settings."""
    return get_agora_settings(user)


@router.put("/settings")
async def update_settings(
    body: AgoraSettingsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update Agora opt-in settings."""
    settings = dict(user.settings or {})
    agora = settings.get("agora", {**DEFAULT_AGORA_SETTINGS})

    if body.enabled is not None:
        agora["enabled"] = body.enabled
    if body.display_name_public is not None:
        agora["display_name_public"] = body.display_name_public
    if body.auto_post_categories is not None:
        cats = agora.get("auto_post_categories", {})
        cats.update(body.auto_post_categories)
        agora["auto_post_categories"] = cats

    settings["agora"] = agora
    user.settings = settings

    # Force SQLAlchemy to detect JSON mutation
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(user, "settings")

    return agora
