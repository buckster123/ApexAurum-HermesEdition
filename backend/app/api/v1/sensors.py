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
        # Core readings
        "temperature_c": raw.get("temperature_c"),
        "humidity_pct": raw.get("humidity_pct"),
        "pressure_hpa": raw.get("pressure_hpa"),
        "co2_ppm": raw.get("co2_ppm") or raw.get("co2_equivalent_ppm"),
        "iaq": raw.get("iaq"),
        "iaq_accuracy": raw.get("iaq_accuracy"),
        "voc_ppm": raw.get("voc_ppm") or raw.get("breath_voc_ppm"),
        # BSEC2 advanced intelligence
        "iaq_accuracy_label": raw.get("iaq_accuracy_label"),
        "co2_accuracy": raw.get("co2_accuracy"),
        "breath_voc_accuracy": raw.get("breath_voc_accuracy"),
        "gas_percentage": raw.get("gas_percentage"),
        "gas_percentage_accuracy": raw.get("gas_percentage_accuracy"),
        "raw_gas_resistance_ohm": raw.get("raw_gas_resistance_ohm"),
        "raw_temperature_c": raw.get("raw_temperature_c"),
        "raw_humidity_pct": raw.get("raw_humidity_pct"),
        "air_quality": raw.get("air_quality"),
        "air_quality_description": raw.get("air_quality_description"),
        "bsec_version": raw.get("bsec_version"),
        "stabilization_status": raw.get("stabilization_status"),
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
    crop: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Capture photo from visual or night camera. Returns base64 JPEG.

    For night camera, crop=true center-crops 16:9 wide-angle to 4:3
    to match the IMX500 FOV for composite overlay alignment.
    """
    device = await _get_user_device(device_id, user, db)
    if camera == CameraType.visual:
        action = "capture_visual"
    elif crop:
        action = "capture_night_cropped"
    else:
        action = "capture_night"
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


@router.get("/{device_id}/sensors/trend")
async def sensor_trend(
    device_id: str,
    hours: float = 3.0,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pressure trend + comfort index from recent telemetry.

    Used by the indoor 'weather' bar. Computes barometric slope (hPa/hr)
    and a simple comfort classification from latest readings.
    """
    device = await _get_user_device(device_id, user, db)
    hours = max(0.5, min(hours, 24.0))

    result = await db.execute(text("""
        SELECT pressure_hpa, temperature_c, humidity_pct, iaq_score,
               EXTRACT(EPOCH FROM created_at) as epoch
        FROM sensor_telemetry
        WHERE device_id = :device_id
          AND created_at > NOW() - make_interval(hours => :hours)
          AND pressure_hpa IS NOT NULL
        ORDER BY created_at ASC
        LIMIT 60
    """), {"device_id": str(device.id), "hours": hours})
    rows = result.mappings().all()

    if len(rows) < 2:
        return {
            "trend": "unknown",
            "pressure_slope_hpa_hr": None,
            "comfort": None,
            "comfort_detail": None,
            "sample_count": len(rows),
        }

    # Linear regression: pressure vs time (least-squares, no numpy)
    n = len(rows)
    sum_x = sum(r["epoch"] for r in rows)
    sum_y = sum(r["pressure_hpa"] for r in rows)
    sum_xy = sum(r["epoch"] * r["pressure_hpa"] for r in rows)
    sum_x2 = sum(r["epoch"] ** 2 for r in rows)
    denom = n * sum_x2 - sum_x ** 2
    if denom == 0:
        slope_per_hr = 0.0
    else:
        slope_per_hr = ((n * sum_xy - sum_x * sum_y) / denom) * 3600

    # Classify trend from slope
    if slope_per_hr < -1.5:
        trend_label = "stormy"
    elif slope_per_hr < -0.5:
        trend_label = "rain_likely"
    elif slope_per_hr <= 0.5:
        trend_label = "stable"
    elif slope_per_hr <= 1.5:
        trend_label = "improving"
    else:
        trend_label = "clear"

    # Comfort index from latest reading
    latest = rows[-1]
    temp = latest.get("temperature_c")
    hum = latest.get("humidity_pct")
    iaq = latest.get("iaq_score")

    comfort_parts = []
    if temp is not None:
        if temp < 18:
            comfort_label = "cool"
        elif temp > 26:
            comfort_label = "warm"
        else:
            comfort_label = "comfortable"
        comfort_parts.append(f"{temp:.1f}C")
    else:
        comfort_label = "unknown"

    if hum is not None:
        if hum > 60 and comfort_label == "comfortable":
            comfort_label = "humid"
        comfort_parts.append(f"{hum:.0f}% RH")

    iaq_text = ""
    if iaq is not None:
        if iaq <= 50:
            iaq_text = "Excellent air"
        elif iaq <= 100:
            iaq_text = "Good air"
        elif iaq <= 150:
            iaq_text = "Moderate air"
        else:
            iaq_text = "Stuffy"
            if comfort_label == "comfortable":
                comfort_label = "stuffy"
        comfort_parts.append(iaq_text)

    return {
        "trend": trend_label,
        "pressure_slope_hpa_hr": round(slope_per_hr, 3),
        "comfort": comfort_label,
        "comfort_detail": ", ".join(comfort_parts) if comfort_parts else None,
        "sample_count": n,
    }


# ─── AI Vision Endpoints ─────────────────────────────────────────────


@router.post("/{device_id}/sensors/ai/detect")
async def sensor_ai_detect(
    device_id: str,
    confidence: float = 0.3,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run object detection on IMX500. Returns COCO-80 detections.

    First call loads the model (~5s). Subsequent calls are fast (~50ms).
    """
    device = await _get_user_device(device_id, user, db)
    confidence = max(0.1, min(confidence, 0.99))
    result = await _send_sensor_command(
        device.id, "detect_objects",
        params={"confidence": confidence},
        timeout=30,
    )
    data = result.get("data", {})
    return {
        "model": data.get("model"),
        "detections": data.get("detections", []),
        "count": data.get("count", 0),
        "performance": data.get("performance"),
        "duration_ms": result.get("duration_ms", 0),
        "device_name": device.device_name,
    }


@router.post("/{device_id}/sensors/ai/classify")
async def sensor_ai_classify(
    device_id: str,
    top_k: int = 5,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run scene classification on IMX500. Returns ImageNet top-K predictions.

    First call loads the model (~5s). Subsequent calls are fast (~10ms).
    """
    device = await _get_user_device(device_id, user, db)
    top_k = max(1, min(top_k, 20))
    result = await _send_sensor_command(
        device.id, "classify_scene",
        params={"top_k": top_k},
        timeout=30,
    )
    data = result.get("data", {})
    return {
        "model": data.get("model"),
        "predictions": data.get("predictions", []),
        "performance": data.get("performance"),
        "duration_ms": result.get("duration_ms", 0),
        "device_name": device.device_name,
    }


@router.post("/{device_id}/sensors/ai/pose")
async def sensor_ai_pose(
    device_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Run pose estimation on IMX500. Returns 17 body keypoints.

    First call loads the model (~5s). Subsequent calls are fast (~30ms).
    """
    device = await _get_user_device(device_id, user, db)
    result = await _send_sensor_command(
        device.id, "estimate_poses",
        timeout=30,
    )
    data = result.get("data", {})
    return {
        "model": data.get("model"),
        "poses": data.get("poses", []),
        "people_detected": data.get("people_detected", 0),
        "performance": data.get("performance"),
        "duration_ms": result.get("duration_ms", 0),
        "device_name": device.device_name,
    }
