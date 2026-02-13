"""Universal Memory Import API — The Transmuter.

POST /cortex/import/detect   — Upload file, auto-detect format, return preview
POST /cortex/import/commit   — Commit import with SSE progress streaming
GET  /cortex/import/limits   — User's import quota based on tier

"The Crucible accepts all raw materials."
"""

import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.config import TIER_LIMITS
from app.database import get_db
from app.services.cerebro.importers import detect_and_parse, ParseResult

logger = logging.getLogger("cerebro-import-api")

router = APIRouter(prefix="/cortex/import", tags=["Memory Import"])

# In-memory parse cache (import_token -> ParseResult)
# Entries expire after 15 minutes
_parse_cache: dict[str, dict] = {}
CACHE_TTL = 15 * 60  # 15 minutes


def _cache_cleanup():
    """Remove expired cache entries."""
    now = time.time()
    expired = [k for k, v in _parse_cache.items() if now - v["ts"] > CACHE_TTL]
    for k in expired:
        del _parse_cache[k]


def _make_token(content_hash: str, user_id: str) -> str:
    """Create a simple import token from content hash + user_id."""
    raw = f"{content_hash}:{user_id}:{int(time.time())}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


# =============================================================================
# Schemas
# =============================================================================

class PreviewMemory(BaseModel):
    content: str
    content_full_length: int
    memory_type: Optional[str] = None
    tags: list[str] = []
    agent_id: Optional[str] = None
    salience: Optional[float] = None
    source_index: int = 0


class ImportPreview(BaseModel):
    format_detected: str
    total_memories: int
    preview: list[PreviewMemory]
    warnings: list[str] = []
    metadata: dict = {}
    import_token: str


class ImportCommitRequest(BaseModel):
    import_token: str
    agent_id: str = "AZOTH"
    default_memory_type: Optional[str] = None
    default_tags: list[str] = Field(default_factory=list)
    default_visibility: str = "private"
    selected_indices: Optional[list[int]] = None
    queue_for_dream: bool = False


class ImportLimits(BaseModel):
    imports_per_month: Optional[int]
    imports_used: int
    max_file_mb: int
    tier: str


# =============================================================================
# Helpers
# =============================================================================

async def _get_tier_config(db: AsyncSession, user):
    """Get user's tier config with quest tier resolution."""
    from app.services.billing import get_user_subscription
    sub = await get_user_subscription(db, user.id)
    tier = sub.tier if sub else "free_trial"

    # Resolve quest tiers
    from app.config import QUEST_TIER_MAP
    base_tier = QUEST_TIER_MAP.get(tier, tier)

    return tier, TIER_LIMITS.get(base_tier, TIER_LIMITS["free_trial"])


async def _count_imports_this_month(db: AsyncSession, user_id: UUID) -> int:
    """Count memories imported this billing period."""
    from sqlalchemy import text
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        text("""
            SELECT COUNT(*) FROM cerebro_memory_nodes
            WHERE user_id = :uid AND source = 'import'
            AND created_at >= :start
        """),
        {"uid": str(user_id), "start": month_start},
    )
    row = result.first()
    return row[0] if row else 0


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/detect", response_model=ImportPreview)
async def detect_and_preview(
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload file, auto-detect format, parse, and return preview.

    Does NOT store anything — just parses and returns what would be imported.
    """
    tier, tier_config = await _get_tier_config(db, user)

    # Tier gate (admin bypass)
    max_imports = tier_config.get("memory_imports_per_month", 0)
    if max_imports == 0 and not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=403,
            detail=f"Memory import requires Seeker tier or above (current: {tier})",
        )

    # File size check
    max_mb = tier_config.get("import_max_file_mb", 5)
    if getattr(user, "is_admin", False):
        max_mb = 50  # Admin gets max
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > max_mb:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f}MB). Your tier allows up to {max_mb}MB.",
        )

    # Parse
    filename = file.filename or "unknown.txt"
    result = detect_and_parse(filename, content)

    if not result.memories:
        return ImportPreview(
            format_detected=result.format_detected,
            total_memories=0,
            preview=[],
            warnings=result.warnings or ["No memories found in file"],
            metadata=result.metadata,
            import_token="",
        )

    # Cache parsed result
    _cache_cleanup()
    content_hash = hashlib.sha256(content).hexdigest()[:16]
    token = _make_token(content_hash, str(user.id))
    _parse_cache[token] = {
        "result": result,
        "user_id": str(user.id),
        "ts": time.time(),
    }

    # Build preview (first 50 memories, truncated)
    preview = []
    for mem in result.memories[:50]:
        preview.append(PreviewMemory(
            content=mem.content[:200],
            content_full_length=len(mem.content),
            memory_type=mem.memory_type,
            tags=mem.tags[:10],
            agent_id=mem.agent_id,
            salience=mem.salience,
            source_index=mem.source_index,
        ))

    return ImportPreview(
        format_detected=result.format_detected,
        total_memories=len(result.memories),
        preview=preview,
        warnings=result.warnings[:10],
        metadata=result.metadata,
        import_token=token,
    )


@router.post("/commit")
async def commit_import(
    request: ImportCommitRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Commit the import. Streams SSE progress events.

    Uses the import_token from detect to retrieve cached parse results.
    """
    # Retrieve cached parse
    cached = _parse_cache.get(request.import_token)
    if not cached:
        raise HTTPException(status_code=410, detail="Import preview expired. Please re-upload the file.")
    if cached["user_id"] != str(user.id):
        raise HTTPException(status_code=403, detail="Import token does not belong to this user.")

    result: ParseResult = cached["result"]

    # Tier quota check
    tier, tier_config = await _get_tier_config(db, user)
    max_imports = tier_config.get("memory_imports_per_month")
    is_admin = getattr(user, "is_admin", False)

    if max_imports is not None and not is_admin:
        used = await _count_imports_this_month(db, user.id)
        remaining = max(0, max_imports - used)
        if remaining == 0:
            raise HTTPException(
                status_code=429,
                detail=f"Import quota reached ({used}/{max_imports} this month).",
            )

    # Filter selected indices if specified
    memories = result.memories
    if request.selected_indices is not None:
        selected = set(request.selected_indices)
        memories = [m for m in memories if m.source_index in selected]

    # Apply quota cap (only import up to remaining quota)
    if max_imports is not None and not is_admin:
        used = await _count_imports_this_month(db, user.id)
        remaining = max(0, max_imports - used)
        if len(memories) > remaining:
            memories = memories[:remaining]

    async def stream_import():
        """SSE generator for import progress."""
        from app.services.cerebro.service import get_cerebro_service
        from app.database import get_db_context

        svc = get_cerebro_service()
        imported = 0
        skipped = 0
        errors = 0
        total = len(memories)
        new_memory_ids = []
        start_time = time.time()

        for i, mem in enumerate(memories):
            try:
                async with get_db_context() as import_db:
                    # Apply overrides
                    agent_id = request.agent_id or mem.agent_id or "AZOTH"
                    memory_type = request.default_memory_type or mem.memory_type or "semantic"
                    tags = list(set(mem.tags + request.default_tags))
                    visibility = request.default_visibility or mem.visibility or "private"
                    salience = mem.salience or 0.5

                    result_dict = await svc.remember(
                        import_db,
                        user.id,
                        mem.content,
                        memory_type=memory_type,
                        tags=tags,
                        salience=salience,
                        agent_id=agent_id,
                        visibility=visibility,
                        source="import",
                    )

                    if result_dict and result_dict.get("action") == "stored":
                        imported += 1
                        if result_dict.get("id"):
                            new_memory_ids.append(result_dict["id"])
                    else:
                        skipped += 1

            except Exception as e:
                errors += 1
                yield f"event: error\ndata: {json.dumps({'index': mem.source_index, 'error': str(e)[:200]})}\n\n"

            # Progress every 5 items or on last item
            if (i + 1) % 5 == 0 or i == total - 1:
                percent = round(((i + 1) / total) * 100) if total > 0 else 100
                yield f"event: progress\ndata: {json.dumps({'imported': imported, 'skipped': skipped, 'errors': errors, 'total': total, 'current': i + 1, 'percent': percent})}\n\n"

        # Queue for dream if requested
        queued_for_dream = 0
        if request.queue_for_dream and new_memory_ids:
            try:
                async with get_db_context() as dream_db:
                    from app.services.cerebro.pg_graph_store import PgGraphStore
                    store = PgGraphStore(dream_db)
                    queued_for_dream = await store.add_to_dream_queue(
                        user.id, new_memory_ids, source="import",
                    )
            except Exception as e:
                logger.warning(f"Failed to queue imports for dream: {e}")

        # Clean up cache
        _parse_cache.pop(request.import_token, None)

        duration = round(time.time() - start_time, 2)
        yield f"event: complete\ndata: {json.dumps({'imported': imported, 'skipped': skipped, 'errors': errors, 'total': total, 'duration_seconds': duration, 'queued_for_dream': queued_for_dream})}\n\n"

    return StreamingResponse(
        stream_import(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/limits", response_model=ImportLimits)
async def get_import_limits(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return user's import quota based on tier."""
    tier, tier_config = await _get_tier_config(db, user)
    max_imports = tier_config.get("memory_imports_per_month", 0)
    max_file_mb = tier_config.get("import_max_file_mb", 0)

    is_admin = getattr(user, "is_admin", False)
    if is_admin:
        max_imports = None
        max_file_mb = 50

    used = await _count_imports_this_month(db, user.id)

    return ImportLimits(
        imports_per_month=max_imports,
        imports_used=used,
        max_file_mb=max_file_mb,
        tier=tier,
    )
