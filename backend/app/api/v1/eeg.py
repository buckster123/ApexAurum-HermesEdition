"""
EEG / BCI Dashboard REST API

Direct EEG access bypassing the LLM — reads go straight through
the Bridge WebSocket tunnel to the OpenBCI hardware.

"The bridge between brain and silicon"
"""

import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.device import Device
from app.models.user import User
from app.services.bridge_manager import get_bridge_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["EEG Dashboard"])


# ─── Helpers ────────────────────────────────────────────────────────


async def _get_user_eeg_device(
    device_id: str, user: User, db: AsyncSession
) -> Device:
    """Fetch an EEG device owned by the given user, or raise 404."""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    if device.device_type != "eeg_headset":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Device is not an EEG headset")
    return device


async def _send_eeg_command(
    device_id: UUID,
    action: str,
    params: dict | None = None,
    timeout: float = 15.0,
) -> dict:
    """Send command to EEG headset via bridge, return result or raise HTTPException."""
    manager = get_bridge_manager()
    if not manager.is_connected(device_id):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EEG headset is offline",
        )
    try:
        return await manager.send_command(device_id, action, params or {}, timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"EEG headset did not respond within {timeout}s",
        )
    except ConnectionError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="EEG headset disconnected during command",
        )
    except RuntimeError as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"EEG headset error: {e}",
        )


# ─── Endpoints ──────────────────────────────────────────────────────


@router.get("/{device_id}/eeg/status")
async def eeg_status(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get EEG board connection status, streaming state, and board info.
    Combines bridge connection state with live device query.
    """
    device = await _get_user_eeg_device(device_id, user, db)
    manager = get_bridge_manager()
    online = manager.is_connected(device.id)

    result = {
        "device_id": str(device.id),
        "device_name": device.device_name,
        "device_type": device.device_type,
        "online": online,
    }

    if online:
        # Query live status from device
        try:
            live = await _send_eeg_command(device.id, "eeg_status", timeout=10)
            result["board"] = live.get("data", {})
        except HTTPException:
            result["board"] = None

        # Include cached telemetry if available
        telemetry = manager.get_telemetry(device.id)
        if telemetry:
            result["telemetry"] = telemetry

    return result


@router.get("/{device_id}/eeg/emotion")
async def eeg_emotion(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get current real-time emotion snapshot from active EEG stream.
    Returns valence, arousal, attention, engagement, and chills detection.
    """
    device = await _get_user_eeg_device(device_id, user, db)

    live = await _send_eeg_command(device.id, "eeg_realtime_emotion", timeout=10)
    data = live.get("data", {})

    return {
        "device_name": device.device_name,
        **data,
    }


@router.get("/{device_id}/eeg/sessions")
async def eeg_sessions(
    device_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List recorded EEG sessions. Pulls from both Cloud database and
    device-side storage (via bridge).
    """
    device = await _get_user_eeg_device(device_id, user, db)

    # Query Cloud-stored sessions
    result = await db.execute(
        text("""
            SELECT session_id, track_title, listener, duration_ms,
                   summary, created_at
            FROM eeg_sessions
            WHERE device_id = :did AND user_id = :uid
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"did": str(device.id), "uid": str(user.id), "limit": limit},
    )

    sessions = []
    for row in result.mappings().all():
        summary = row["summary"]
        if isinstance(summary, str):
            summary = json.loads(summary) if summary else {}
        sessions.append({
            "session_id": row["session_id"],
            "track_title": row["track_title"],
            "listener": row["listener"],
            "duration_ms": row["duration_ms"],
            "chills_count": summary.get("chills_count", 0) if summary else 0,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "source": "cloud",
        })

    # Also query device if online
    manager = get_bridge_manager()
    if manager.is_connected(device.id):
        try:
            live = await _send_eeg_command(
                device.id, "eeg_list_sessions", {"limit": limit}, timeout=10
            )
            device_sessions = live.get("data", {}).get("sessions", [])
            # Merge — mark device-only sessions
            cloud_ids = {s["session_id"] for s in sessions}
            for ds in device_sessions:
                if ds.get("session_id") not in cloud_ids:
                    ds["source"] = "device"
                    sessions.append(ds)
        except HTTPException:
            pass  # Device offline during query — just show cloud sessions

    return {
        "sessions": sessions,
        "count": len(sessions),
        "device_name": device.device_name,
    }


@router.get("/{device_id}/eeg/sessions/{session_id}")
async def eeg_session_detail(
    device_id: str,
    session_id: str,
    detail_level: str = Query(default="full", regex="^(summary|full|narrative)$"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed session data. Tries Cloud database first, falls back to device.
    """
    device = await _get_user_eeg_device(device_id, user, db)

    # Try Cloud first
    result = await db.execute(
        text("""
            SELECT session_id, track_id, track_title, listener, duration_ms,
                   summary, narrative, moments, created_at
            FROM eeg_sessions
            WHERE device_id = :did AND session_id = :sid
        """),
        {"did": str(device.id), "sid": session_id},
    )
    row = result.mappings().first()

    if row:
        summary = row["summary"]
        if isinstance(summary, str):
            summary = json.loads(summary) if summary else {}
        moments = row["moments"]
        if isinstance(moments, str):
            moments = json.loads(moments) if moments else []

        if detail_level == "narrative":
            return {"session_id": session_id, "narrative": row["narrative"]}
        elif detail_level == "summary":
            return {
                "session_id": session_id,
                "track_title": row["track_title"],
                "listener": row["listener"],
                "duration_ms": row["duration_ms"],
                "summary": summary,
                "narrative": row["narrative"],
            }
        else:
            return {
                "session_id": session_id,
                "track_id": row["track_id"],
                "track_title": row["track_title"],
                "listener": row["listener"],
                "duration_ms": row["duration_ms"],
                "summary": summary,
                "narrative": row["narrative"],
                "moments": moments,
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }

    # Fall back to device
    manager = get_bridge_manager()
    if manager.is_connected(device.id):
        live = await _send_eeg_command(
            device.id,
            "eeg_experience_get",
            {"session_id": session_id, "detail_level": detail_level},
            timeout=15,
        )
        return live.get("data", {})

    raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}")


@router.get("/{device_id}/eeg/telemetry")
async def eeg_telemetry_history(
    device_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent EEG telemetry history (emotion snapshots over time).
    Useful for graphing emotional response curves.
    """
    device = await _get_user_eeg_device(device_id, user, db)

    result = await db.execute(
        text("""
            SELECT valence, arousal, attention, engagement,
                   possible_chills, band_powers, created_at
            FROM eeg_telemetry
            WHERE device_id = :did AND user_id = :uid
            ORDER BY created_at DESC
            LIMIT :limit
        """),
        {"did": str(device.id), "uid": str(user.id), "limit": limit},
    )

    points = []
    for row in result.mappings().all():
        bp = row["band_powers"]
        if isinstance(bp, str):
            bp = json.loads(bp) if bp else {}
        points.append({
            "valence": row["valence"],
            "arousal": row["arousal"],
            "attention": row["attention"],
            "engagement": row["engagement"],
            "possible_chills": row["possible_chills"],
            "band_powers": bp,
            "timestamp": row["created_at"].isoformat() if row["created_at"] else None,
        })

    # Reverse so oldest first (timeline order)
    points.reverse()

    return {
        "telemetry": points,
        "count": len(points),
        "device_name": device.device_name,
    }
