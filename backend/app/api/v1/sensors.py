"""
SensorHead Dashboard REST API

Direct sensor access bypassing the LLM — reads go straight through
the Bridge WebSocket tunnel to the SensorHead hardware.

"The ouroboros sees itself"
"""

import asyncio
import json
import logging
import time
from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.device import Device
from app.models.user import User
from app.services.bridge_manager import get_bridge_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["SensorHead Dashboard"])


class CameraType(str, Enum):
    visual = "visual"
    night = "night"


# ─── Helpers ────────────────────────────────────────────────────────


async def _get_user_device(
    device_id: str, user: User, db: AsyncSession
) -> Device:
    """Fetch a device owned by the given user, or raise 404."""
    result = await db.execute(
        select(Device).where(Device.id == device_id, Device.user_id == user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


async def _send_sensor_command(
    device_id: UUID,
    action: str,
    params: dict | None = None,
    timeout: float = 15.0,
) -> dict:
    """Send command to SensorHead via bridge, return result or raise HTTPException."""
    manager = get_bridge_manager()
    if not manager.is_connected(device_id):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SensorHead is offline",
        )
    try:
        return await manager.send_command(device_id, action, params or {}, timeout=timeout)
    except asyncio.TimeoutError:
        raise HTTPException(
            status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"SensorHead did not respond within {timeout}s",
        )
    except ConnectionError:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SensorHead disconnected during command",
        )
    except RuntimeError as e:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"SensorHead error: {e}",
        )


def _normalize_env(raw: dict | None) -> dict | None:
    """Map raw BME688 field names to dashboard-friendly names."""
    if not raw:
        return raw
    return {
        "temperature_c": raw.get("temperature_c"),
        "humidity_pct": raw.get("humidity_pct"),
        "pressure_hpa": raw.get("pressure_hpa"),
        "co2_ppm": raw.get("co2_ppm") or raw.get("co2_equivalent_ppm"),
        "iaq": raw.get("iaq"),
        "iaq_accuracy": raw.get("iaq_accuracy"),
        "voc_ppm": raw.get("voc_ppm") or raw.get("breath_voc_ppm"),
    }


# ─── Endpoints ──────────────────────────────────────────────────────


@router.get("/{device_id}/sensors")
async def sensor_status(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Connection status + cached telemetry. Always succeeds (even offline)."""
    device = await _get_user_device(device_id, user, db)
    manager = get_bridge_manager()
    online = manager.is_connected(device.id)

    response = {
        "online": online,
        "device_name": device.device_name,
        "device_id": str(device.id),
        "device_type": device.device_type,
    }

    if online:
        conn = manager.get_connection(device.id)
        if conn:
            response["connected_at"] = conn.connected_at
            response["uptime_s"] = round(time.time() - conn.connected_at, 1)
        telemetry = manager.get_telemetry(device.id)
        if telemetry:
            response["telemetry"] = telemetry
    else:
        response["connected_at"] = None
        response["uptime_s"] = None

    # Fallback: last DB telemetry if no cached data
    if "telemetry" not in response:
        try:
            result = await db.execute(text("""
                SELECT temperature_c, humidity_pct, pressure_hpa,
                       co2_ppm, iaq_score, iaq_accuracy, voc_ppm,
                       thermal_min_c, thermal_max_c, thermal_avg_c,
                       created_at
                FROM sensor_telemetry
                WHERE device_id = :device_id
                ORDER BY created_at DESC LIMIT 1
            """), {"device_id": str(device.id)})
            row = result.mappings().first()
            if row:
                response["telemetry"] = {
                    "readings": {
                        "temperature_c": row["temperature_c"],
                        "humidity_pct": row["humidity_pct"],
                        "pressure_hpa": row["pressure_hpa"],
                        "co2_ppm": row["co2_ppm"],
                        "iaq": row["iaq_score"],
                        "iaq_accuracy": row["iaq_accuracy"],
                        "voc_ppm": row["voc_ppm"],
                        "thermal_min_c": row["thermal_min_c"],
                        "thermal_max_c": row["thermal_max_c"],
                        "thermal_avg_c": row["thermal_avg_c"],
                    },
                    "timestamp": row["created_at"].timestamp() if row["created_at"] else None,
                    "age_s": round(time.time() - row["created_at"].timestamp(), 1) if row["created_at"] else None,
                    "source": "database",
                }
        except Exception as e:
            logger.debug(f"Telemetry DB fallback failed: {e}")

    return response


@router.post("/{device_id}/sensors/environment")
async def sensor_environment(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger live BME688 environment read."""
    device = await _get_user_device(device_id, user, db)
    result = await _send_sensor_command(device.id, "sense_environment", timeout=15)
    return {
        "data": _normalize_env(result.get("data")),
        "duration_ms": result.get("duration_ms", 0),
        "device_name": device.device_name,
    }


@router.post("/{device_id}/sensors/capture/{camera}")
async def sensor_capture(
    device_id: str,
    camera: CameraType,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Capture photo from visual or night camera. Returns base64 JPEG."""
    device = await _get_user_device(device_id, user, db)
    action = "capture_visual" if camera == CameraType.visual else "capture_night"
    result = await _send_sensor_command(device.id, action, timeout=20)
    return {
        "image_base64": result.get("data"),
        "camera": camera.value,
        "duration_ms": result.get("duration_ms", 0),
        "device_name": device.device_name,
    }


@router.post("/{device_id}/sensors/thermal")
async def sensor_thermal(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Capture thermal heatmap image. Returns base64 JPEG."""
    device = await _get_user_device(device_id, user, db)
    result = await _send_sensor_command(device.id, "sense_thermal", timeout=15)
    return {
        "image_base64": result.get("data"),
        "sensor": "thermal",
        "duration_ms": result.get("duration_ms", 0),
        "device_name": device.device_name,
    }


@router.post("/{device_id}/sensors/snapshot")
async def sensor_snapshot(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Composite snapshot: environment + all 3 cameras.
    Sequential capture (~6-8s total). Partial results on failure.
    """
    device = await _get_user_device(device_id, user, db)
    manager = get_bridge_manager()

    if not manager.is_connected(device.id):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SensorHead is offline",
        )

    start = time.time()
    errors = []
    snapshot = {
        "environment": None,
        "visual_base64": None,
        "night_base64": None,
        "thermal_base64": None,
    }

    # Sequential captures (Pi can only do one camera at a time)
    steps = [
        ("environment", "sense_environment", 15),
        ("visual_base64", "capture_visual", 20),
        ("night_base64", "capture_night", 20),
        ("thermal_base64", "sense_thermal", 15),
    ]

    for key, action, timeout in steps:
        try:
            result = await manager.send_command(
                device.id, action, {}, timeout=timeout
            )
            data = result.get("data")
            snapshot[key] = _normalize_env(data) if key == "environment" else data
        except Exception as e:
            errors.append(f"{action}: {e}")
            logger.warning(f"Snapshot {action} failed: {e}")

    return {
        **snapshot,
        "errors": errors,
        "total_duration_ms": int((time.time() - start) * 1000),
        "device_name": device.device_name,
    }
