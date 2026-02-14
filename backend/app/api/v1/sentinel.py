"""
SensorHead Sentinel REST API

Control the autonomous motion detection system on SensorHead devices.
Arm/disarm, configure thresholds, manage presets, and query event history.

"The guardian's command center"
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.services.bridge_manager import get_bridge_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["Sentinel"])


# ─── Helpers ────────────────────────────────────────────────────────


async def _get_user_device(device_id: str, user: User, db: AsyncSession):
    """Fetch a device owned by the user, or raise 404."""
    from app.models.device import Device
    from sqlalchemy import select

    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


async def _send_sentinel_command(
    device_id: UUID, action: str, params: dict | None = None, timeout: float = 15.0
) -> dict:
    """Send sentinel command to SensorHead via bridge."""
    manager = get_bridge_manager()
    if not manager.is_connected(device_id):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SensorHead is offline",
        )
    try:
        return await manager.send_command(device_id, action, params or {}, timeout=timeout)
    except Exception as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"SensorHead error: {e}",
        )


# ─── Status ─────────────────────────────────────────────────────────


@router.get("/{device_id}/sentinel/status")
async def sentinel_status(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current sentinel status from device (armed, config, stats)."""
    device = await _get_user_device(device_id, user, db)
    manager = get_bridge_manager()

    if not manager.is_connected(device.id):
        # Return stored config as offline fallback
        row = await db.execute(
            text("SELECT config, active_preset FROM sentinel_config WHERE device_id = :did"),
            {"did": str(device.id)},
        )
        saved = row.mappings().first()
        return {
            "online": False,
            "armed": False,
            "config": json.loads(saved["config"]) if saved and saved["config"] else {},
            "active_preset": saved["active_preset"] if saved else None,
            "device_name": device.device_name,
        }

    result = await _send_sentinel_command(device.id, "sentinel_status")
    data = result.get("data", {})
    return {
        "online": True,
        **data,
        "device_name": device.device_name,
    }


# ─── Arm / Disarm ──────────────────────────────────────────────────


@router.post("/{device_id}/sentinel/arm")
async def sentinel_arm(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Arm the sentinel. Motion detection begins immediately."""
    device = await _get_user_device(device_id, user, db)
    result = await _send_sentinel_command(device.id, "sentinel_arm")
    return {
        "action": "armed",
        **result.get("data", {}),
        "device_name": device.device_name,
    }


@router.post("/{device_id}/sentinel/disarm")
async def sentinel_disarm(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disarm the sentinel. Monitoring stops."""
    device = await _get_user_device(device_id, user, db)
    result = await _send_sentinel_command(device.id, "sentinel_disarm")
    return {
        "action": "disarmed",
        **result.get("data", {}),
        "device_name": device.device_name,
    }


# ─── Configuration ─────────────────────────────────────────────────


@router.post("/{device_id}/sentinel/configure")
async def sentinel_configure(
    device_id: str,
    config: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update sentinel configuration. Hot-applied to running sentinel."""
    device = await _get_user_device(device_id, user, db)

    # Push to device
    result = await _send_sentinel_command(device.id, "sentinel_configure", config)

    # Persist to DB
    try:
        device_config = result.get("data", {}).get("config", config)
        await db.execute(
            text("""
                INSERT INTO sentinel_config (device_id, user_id, config, updated_at)
                VALUES (:did, :uid, :config, NOW())
                ON CONFLICT (device_id)
                DO UPDATE SET config = :config, updated_at = NOW()
            """),
            {
                "did": str(device.id),
                "uid": str(user.id),
                "config": json.dumps(device_config),
            },
        )
        await db.commit()
    except Exception as e:
        logger.debug(f"Sentinel config persist failed: {e}")

    return {
        "action": "configured",
        **result.get("data", {}),
        "device_name": device.device_name,
    }


# ─── Presets ────────────────────────────────────────────────────────


@router.get("/{device_id}/sentinel/presets")
async def sentinel_presets(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available presets (built-in + custom)."""
    device = await _get_user_device(device_id, user, db)

    # Built-in presets (from Pi-side sentinel.py)
    builtins = [
        {
            "name": "default",
            "is_builtin": True,
            "description": "Balanced defaults (2°C threshold, 10px, 30s cooldown)",
        },
        {
            "name": "night_watch",
            "is_builtin": True,
            "description": "Sensitive overnight (1.5°C, 5px, 22:00-07:00)",
        },
        {
            "name": "away_mode",
            "is_builtin": True,
            "description": "High sensitivity, person-only (1.0°C, 3px, 15s cooldown)",
        },
        {
            "name": "pet_watch",
            "is_builtin": True,
            "description": "Pet-focused (2.5°C, 8px, cats/dogs/birds)",
        },
    ]

    # User custom presets
    result = await db.execute(
        text("SELECT id, name, config, created_at FROM sentinel_presets WHERE user_id = :uid ORDER BY name"),
        {"uid": str(user.id)},
    )
    customs = [
        {
            "id": str(row["id"]),
            "name": row["name"],
            "is_builtin": False,
            "config": row["config"] if isinstance(row["config"], dict) else (json.loads(row["config"]) if row["config"] else {}),
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in result.mappings().all()
    ]

    return {
        "presets": builtins + customs,
        "device_name": device.device_name,
    }


@router.post("/{device_id}/sentinel/presets/{preset_name}/load")
async def sentinel_load_preset(
    device_id: str,
    preset_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Load a preset onto the device. Built-in or custom."""
    device = await _get_user_device(device_id, user, db)

    # Check if it's a custom preset
    result = await db.execute(
        text("SELECT config FROM sentinel_presets WHERE user_id = :uid AND name = :name"),
        {"uid": str(user.id), "name": preset_name},
    )
    custom = result.mappings().first()

    if custom:
        # Custom preset — send config values to device
        config = json.loads(custom["config"]) if custom["config"] else {}
        cmd_result = await _send_sentinel_command(
            device.id, "sentinel_configure", config
        )
    else:
        # Built-in preset — device handles it
        cmd_result = await _send_sentinel_command(
            device.id, "sentinel_load_preset", {"preset": preset_name}
        )

    # Remember active preset
    try:
        await db.execute(
            text("""
                INSERT INTO sentinel_config (device_id, user_id, active_preset, updated_at)
                VALUES (:did, :uid, :preset, NOW())
                ON CONFLICT (device_id)
                DO UPDATE SET active_preset = :preset, updated_at = NOW()
            """),
            {"did": str(device.id), "uid": str(user.id), "preset": preset_name},
        )
        await db.commit()
    except Exception as e:
        logger.debug(f"Preset tracking failed: {e}")

    return {
        "action": "preset_loaded",
        "preset": preset_name,
        **cmd_result.get("data", {}),
        "device_name": device.device_name,
    }


@router.post("/{device_id}/sentinel/presets")
async def sentinel_save_preset(
    device_id: str,
    body: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save current config (or provided config) as a custom preset."""
    device = await _get_user_device(device_id, user, db)

    name = body.get("name")
    config = body.get("config")

    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Preset name required")

    # If no config provided, fetch current config from device
    if not config:
        manager = get_bridge_manager()
        if manager.is_connected(device.id):
            result = await _send_sentinel_command(device.id, "sentinel_status")
            config = result.get("data", {}).get("config", {})
        else:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Device offline — provide config in request body",
            )

    await db.execute(
        text("""
            INSERT INTO sentinel_presets (user_id, name, config)
            VALUES (:uid, :name, :config)
            ON CONFLICT (user_id, name)
            DO UPDATE SET config = :config
        """),
        {
            "uid": str(user.id),
            "name": name,
            "config": json.dumps(config),
        },
    )
    await db.commit()

    return {"action": "preset_saved", "name": name, "config": config}


@router.delete("/{device_id}/sentinel/presets/{preset_name}")
async def sentinel_delete_preset(
    device_id: str,
    preset_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a custom preset."""
    await _get_user_device(device_id, user, db)

    result = await db.execute(
        text("DELETE FROM sentinel_presets WHERE user_id = :uid AND name = :name AND NOT is_builtin"),
        {"uid": str(user.id), "name": preset_name},
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Preset not found or is built-in")

    return {"action": "preset_deleted", "name": preset_name}


# ─── Events Timeline ───────────────────────────────────────────────


@router.get("/{device_id}/sentinel/events")
async def sentinel_events(
    device_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = None,
    unacked_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query sentinel event timeline. Supports filtering and pagination."""
    device = await _get_user_device(device_id, user, db)

    where_clauses = [
        "device_id = :did",
        "(alert_type LIKE 'sentinel_%' OR alert_type LIKE 'pocket_%')",
    ]
    params = {"did": str(device.id), "limit": limit, "offset": offset}

    if event_type:
        where_clauses.append("(alert_type = :etype OR alert_type = :ptype)")
        params["etype"] = f"sentinel_{event_type}"
        params["ptype"] = f"pocket_{event_type}"

    if unacked_only:
        where_clauses.append("acknowledged = FALSE")

    where_sql = " AND ".join(where_clauses)

    # Events
    result = await db.execute(
        text(f"""
            SELECT id, alert_type, data, acknowledged, created_at
            FROM sensor_alerts
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        params,
    )
    events = []
    for row in result.mappings().all():
        raw = row["data"]
        event_data = raw if isinstance(raw, dict) else (json.loads(raw) if raw else {})
        alert_type = row["alert_type"]
        is_pocket = alert_type.startswith("pocket_")
        event_type_name = alert_type.replace("pocket_", "").replace("sentinel_", "")
        events.append({
            "id": str(row["id"]),
            "type": event_type_name,
            "source": "pocket" if is_pocket else "sensorhead",
            "data": event_data,
            "acknowledged": row["acknowledged"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "has_snapshot": bool(event_data.get("snapshot_b64")),
        })

    # Total count
    count_result = await db.execute(
        text(f"SELECT COUNT(*) as cnt FROM sensor_alerts WHERE {where_sql}"),
        {k: v for k, v in params.items() if k not in ("limit", "offset")},
    )
    total = count_result.scalar() or 0

    # Unacked count
    unacked_result = await db.execute(
        text("""
            SELECT COUNT(*) FROM sensor_alerts
            WHERE device_id = :did
              AND (alert_type LIKE 'sentinel_%' OR alert_type LIKE 'pocket_%')
              AND acknowledged = FALSE
        """),
        {"did": str(device.id)},
    )
    unacked_count = unacked_result.scalar() or 0

    return {
        "events": events,
        "total": total,
        "unacked_count": unacked_count,
        "limit": limit,
        "offset": offset,
        "device_name": device.device_name,
    }


@router.get("/{device_id}/sentinel/events/{event_id}/snapshot")
async def sentinel_event_snapshot(
    device_id: str,
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the base64 snapshot image from a sentinel event."""
    device = await _get_user_device(device_id, user, db)

    result = await db.execute(
        text("""
            SELECT data FROM sensor_alerts
            WHERE id = :eid AND device_id = :did
        """),
        {"eid": event_id, "did": str(device.id)},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")

    data = row["data"] if isinstance(row["data"], dict) else (json.loads(row["data"]) if row["data"] else {})
    snapshot = data.get("snapshot_b64")
    if not snapshot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="No snapshot for this event")

    return {"image_base64": snapshot, "event_id": event_id}


# ─── Acknowledge ────────────────────────────────────────────────────


@router.post("/{device_id}/sentinel/events/{event_id}/ack")
async def sentinel_ack_event(
    device_id: str,
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a sentinel event."""
    device = await _get_user_device(device_id, user, db)

    result = await db.execute(
        text("""
            UPDATE sensor_alerts SET acknowledged = TRUE
            WHERE id = :eid AND device_id = :did
            RETURNING id
        """),
        {"eid": event_id, "did": str(device.id)},
    )
    await db.commit()

    if not result.first():
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Event not found")

    return {"action": "acknowledged", "event_id": event_id}


@router.post("/{device_id}/sentinel/events/ack-all")
async def sentinel_ack_all(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge all unacknowledged sentinel events for a device."""
    device = await _get_user_device(device_id, user, db)

    result = await db.execute(
        text("""
            UPDATE sensor_alerts SET acknowledged = TRUE
            WHERE device_id = :did AND alert_type LIKE 'sentinel_%' AND acknowledged = FALSE
        """),
        {"did": str(device.id)},
    )
    await db.commit()

    return {"action": "all_acknowledged", "count": result.rowcount}


# ─── Stats ──────────────────────────────────────────────────────────


@router.get("/{device_id}/sentinel/stats")
async def sentinel_stats(
    device_id: str,
    hours: float = Query(default=24.0, ge=1, le=168),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sentinel event statistics over the given time window."""
    device = await _get_user_device(device_id, user, db)

    result = await db.execute(
        text("""
            SELECT
                alert_type,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE acknowledged = FALSE) as unacked
            FROM sensor_alerts
            WHERE device_id = :did
              AND alert_type LIKE 'sentinel_%'
              AND created_at > NOW() - make_interval(hours => :hours)
            GROUP BY alert_type
            ORDER BY count DESC
        """),
        {"did": str(device.id), "hours": hours},
    )

    by_type = {}
    total = 0
    for row in result.mappings().all():
        event_type = row["alert_type"].replace("sentinel_", "")
        by_type[event_type] = {"count": row["count"], "unacked": row["unacked"]}
        total += row["count"]

    return {
        "hours": hours,
        "total_events": total,
        "by_type": by_type,
        "device_name": device.device_name,
    }
