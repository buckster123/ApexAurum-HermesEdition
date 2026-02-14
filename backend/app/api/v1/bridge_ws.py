"""
Bridge WebSocket Routes

Bidirectional WebSocket tunnel between cloud and SensorHead devices.
SensorHead connects outward to this endpoint, then commands flow back
through the tunnel and results return forward.

"The bridge between worlds"
"""

import json
import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.auth.password import verify_password
from app.database import async_session
from app.models.device import Device
from app.models.user import User
from app.services.bridge_manager import get_bridge_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Bridge WebSocket"])

DEVICE_TOKEN_PREFIX = "apex_dev_"
DEVICE_TOKEN_PREFIX_LEN = 13


async def authenticate_device_ws(websocket: WebSocket) -> tuple | None:
    """
    Authenticate SensorHead WebSocket via apex_dev_ token in query param.

    Returns (Device, User) tuple on success, None on failure.
    Uses same token validation as device_deps.py but adapted for WS context.
    """
    token = websocket.query_params.get("token")
    if not token or not token.startswith(DEVICE_TOKEN_PREFIX):
        return None

    token_prefix = token[:DEVICE_TOKEN_PREFIX_LEN]

    async with async_session() as db:
        result = await db.execute(
            select(Device)
            .where(Device.token_prefix == token_prefix)
            .where(Device.status == "active")
        )
        candidates = result.scalars().all()

        for device in candidates:
            if verify_password(token, device.token_hash):
                # Verify it's a sensor_head device
                if device.device_type != "sensor_head":
                    logger.warning(
                        f"Non-sensor_head device attempted bridge connection: "
                        f"{device.id} (type={device.device_type})"
                    )
                    return None

                # Load owner
                user_result = await db.execute(
                    select(User).where(User.id == device.user_id)
                )
                user = user_result.scalar_one_or_none()
                if not user:
                    return None

                return device, user

    return None


async def _touch_device(device_id: UUID):
    """Update device last_seen_at in database."""
    try:
        from app.database import get_db_context
        async with get_db_context() as db:
            await db.execute(
                __import__("sqlalchemy").text(
                    "UPDATE devices SET last_seen_at = :now WHERE id = :id"
                ),
                {"now": datetime.utcnow(), "id": str(device_id)},
            )
            await db.commit()
    except Exception as e:
        logger.debug(f"Failed to update last_seen_at: {e}")


@router.websocket("/bridge")
async def bridge_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for SensorHead devices.

    Connect: ws://host/ws/bridge?token=apex_dev_...

    Cloud→Device messages:
    - command: Execute a sensor action (sense_environment, capture_visual, etc.)

    Device→Cloud messages:
    - response: Result of a command execution
    - telemetry: Periodic sensor readings push
    - alert: Autonomous monitoring alerts (motion, air quality)
    - ping/pong: Keepalive
    """
    auth = await authenticate_device_ws(websocket)
    if not auth:
        await websocket.accept()
        await websocket.close(code=1008, reason="Unauthorized")
        return

    device, user = auth
    device_id = device.id
    user_id = user.id

    await websocket.accept()

    manager = get_bridge_manager()
    manager.register(
        device_id=device_id,
        user_id=user_id,
        websocket=websocket,
        device_name=device.device_name,
    )

    # Mark device as seen
    await _touch_device(device_id)

    # Broadcast connection event to Village
    try:
        from app.services.village_events import (
            get_village_broadcaster, VillageEvent, EventType,
        )
        broadcaster = get_village_broadcaster()
        await broadcaster.broadcast(VillageEvent(
            type=EventType.CONNECTION,
            agent_id="SYSTEM",
            zone="sensor_tower",
            message=f"SensorHead '{device.device_name}' connected",
        ))
    except Exception:
        pass  # Non-fatal

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from SensorHead {device_id}")
                continue

            msg_type = msg.get("type")

            if msg_type == "response":
                # Response to a command — resolve the pending Future
                cmd_id = msg.get("id")
                if cmd_id:
                    resolved = manager.resolve_command(cmd_id, msg)
                    if not resolved:
                        logger.debug(f"Orphaned response: {cmd_id}")

            elif msg_type == "telemetry":
                # Periodic sensor readings
                readings = msg.get("readings", {})
                timestamp = msg.get("timestamp")
                accepted = manager.update_telemetry(device_id, readings, timestamp)

                if accepted:
                    # Store to database and update last_seen
                    try:
                        await _store_telemetry(device_id, user_id, readings)
                        await _touch_device(device_id)
                    except Exception as e:
                        logger.debug(f"Telemetry store failed: {e}")

            elif msg_type == "inference_response":
                # Response from local LLM inference (Bridge relay)
                cmd_id = msg.get("id")
                if cmd_id:
                    resolved = manager.resolve_command(cmd_id, msg)
                    if not resolved:
                        logger.debug(f"Orphaned inference response: {cmd_id}")

            elif msg_type == "alert":
                # Autonomous monitoring alert
                await _handle_alert(device_id, user_id, device.device_name, msg)

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "pong":
                pass  # Keepalive response

    except WebSocketDisconnect:
        manager.unregister(device_id)
        logger.info(f"SensorHead disconnected: {device.device_name}")
    except Exception as e:
        logger.error(f"Bridge WebSocket error: {e}")
        manager.unregister(device_id)

    # Broadcast disconnection event to Village
    try:
        from app.services.village_events import (
            get_village_broadcaster, VillageEvent, EventType,
        )
        broadcaster = get_village_broadcaster()
        await broadcaster.broadcast(VillageEvent(
            type=EventType.CONNECTION,
            agent_id="SYSTEM",
            zone="sensor_tower",
            message=f"SensorHead '{device.device_name}' disconnected",
        ))
    except Exception:
        pass


async def _store_telemetry(device_id: UUID, user_id: UUID, readings: dict):
    """Store telemetry reading to database."""
    from app.database import get_db_context

    async with get_db_context() as db:
        await db.execute(
            __import__("sqlalchemy").text("""
                INSERT INTO sensor_telemetry
                    (device_id, user_id, temperature_c, humidity_pct, pressure_hpa,
                     co2_ppm, iaq_score, iaq_accuracy, voc_ppm,
                     thermal_min_c, thermal_max_c, thermal_avg_c, raw_data)
                VALUES
                    (:device_id, :user_id, :temp, :humidity, :pressure,
                     :co2, :iaq, :iaq_acc, :voc,
                     :t_min, :t_max, :t_avg, :raw)
            """),
            {
                "device_id": str(device_id),
                "user_id": str(user_id),
                "temp": readings.get("temperature_c"),
                "humidity": readings.get("humidity_pct"),
                "pressure": readings.get("pressure_hpa"),
                "co2": readings.get("co2_equivalent_ppm") or readings.get("co2_ppm"),
                "iaq": readings.get("iaq"),
                "iaq_acc": readings.get("iaq_accuracy"),
                "voc": readings.get("breath_voc_ppm") or readings.get("voc_ppm"),
                "t_min": readings.get("thermal_min_c"),
                "t_max": readings.get("thermal_max_c"),
                "t_avg": readings.get("thermal_avg_c"),
                "raw": json.dumps(readings),
            },
        )
        await db.commit()


async def _handle_alert(
    device_id: UUID,
    user_id: UUID,
    device_name: str,
    msg: dict,
):
    """Handle autonomous alert from SensorHead.

    Stores to sensor_alerts, broadcasts to Village WebSocket,
    and pushes sentinel alerts to pocket_pending_messages for
    mobile notification delivery.
    """
    alert_type = msg.get("alert_type", "unknown")
    alert_data = msg.get("data", {})
    is_sentinel = alert_type.startswith("sentinel_")

    logger.info(f"SensorHead alert: {alert_type} from {device_name}")

    # Store alert
    try:
        from app.database import get_db_context

        async with get_db_context() as db:
            await db.execute(
                __import__("sqlalchemy").text("""
                    INSERT INTO sensor_alerts
                        (device_id, user_id, alert_type, data)
                    VALUES (:device_id, :user_id, :alert_type, :data)
                """),
                {
                    "device_id": str(device_id),
                    "user_id": str(user_id),
                    "alert_type": alert_type,
                    "data": json.dumps(alert_data),
                },
            )
            await db.commit()
    except Exception as e:
        logger.warning(f"Failed to store alert: {e}")

    # Push sentinel alerts to mobile notification queue
    if is_sentinel:
        try:
            from app.database import get_db_context

            event_type = alert_data.get("event_type", "motion")
            changed = alert_data.get("changed_pixels", 0)
            delta = alert_data.get("thermal_delta", 0)
            ai_count = len(alert_data.get("ai_detections", []))
            ai_text = f" ({ai_count} AI detections)" if ai_count else ""

            notify_text = (
                f"[Sentinel] {event_type.title()} detected on {device_name} "
                f"— {changed}px, {delta}°C delta{ai_text}"
            )

            async with get_db_context() as db:
                await db.execute(
                    __import__("sqlalchemy").text("""
                        INSERT INTO pocket_pending_messages
                            (user_id, agent_id, text, event_type, source_id)
                        VALUES (:user_id, 'SYSTEM', :text, :event_type, :source_id)
                    """),
                    {
                        "user_id": str(user_id),
                        "text": notify_text,
                        "event_type": "sentinel_alert",
                        "source_id": f"sentinel_{device_name}",
                    },
                )
                await db.commit()
        except Exception as e:
            logger.debug(f"Sentinel mobile notification failed: {e}")

    # Broadcast to Village
    try:
        from app.services.village_events import (
            get_village_broadcaster, VillageEvent, EventType,
        )
        broadcaster = get_village_broadcaster()

        if is_sentinel:
            event_type = alert_data.get("event_type", "motion")
            message = (
                f"[{device_name}] Sentinel: {event_type.title()} detected "
                f"({alert_data.get('changed_pixels', 0)}px)"
            )
        else:
            message = f"[{device_name}] {alert_type}: {json.dumps(alert_data)[:150]}"

        await broadcaster.broadcast(VillageEvent(
            type=EventType.TOOL_COMPLETE,
            agent_id="SYSTEM",
            zone="sensor_tower",
            message=message,
        ))
    except Exception:
        pass
