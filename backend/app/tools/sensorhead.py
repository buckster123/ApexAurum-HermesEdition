"""
SensorHead Proxy Tools

Tools that route through the Bridge WebSocket tunnel to connected
SensorHead hardware. Gives AI agents physical senses — sight, smell,
temperature, and object detection through real-world cameras and sensors.

"Eyes, nose, and skin for the mind"
"""

import asyncio
import json
import logging

from . import registry
from .base import BaseTool, ToolSchema, ToolResult, ToolContext, ToolCategory

logger = logging.getLogger(__name__)


async def _bridge_command(
    context: ToolContext,
    action: str,
    params: dict | None = None,
    timeout: float = 30.0,
    device_name: str | None = None,
) -> ToolResult:
    """
    Common helper: find user's SensorHead and send a command.

    Returns ToolResult with the response data, or an error if
    the device isn't connected or the command fails.
    """
    from app.services.bridge_manager import get_bridge_manager

    manager = get_bridge_manager()
    conn = manager.find_device_for_user(context.user_id, device_name)

    if not conn:
        return ToolResult(
            success=False,
            error=(
                "No SensorHead connected. "
                "Check that your SensorHead is powered on and the bridge service is running."
            ),
        )

    try:
        result = await manager.send_command(
            conn.device_id, action, params or {}, timeout=timeout
        )
        data_type = result.get("data_type", "json")
        metadata = {
            "device_name": conn.device_name,
            "data_type": data_type,
            "device_duration_ms": result.get("duration_ms", 0),
        }

        # Image results: set metadata so ToolResult.to_claude_format()
        # generates a proper image content block for Claude vision
        if data_type == "image_base64":
            metadata["media_type"] = "image/jpeg"
            metadata["caption"] = f"Image from SensorHead '{conn.device_name}' ({action})"

        return ToolResult(
            success=True,
            result=result.get("data"),
            metadata=metadata,
        )
    except asyncio.TimeoutError:
        return ToolResult(
            success=False,
            error=f"SensorHead did not respond within {timeout}s. The sensor may be busy or offline.",
        )
    except ConnectionError as e:
        return ToolResult(success=False, error=str(e))
    except RuntimeError as e:
        return ToolResult(success=False, error=f"SensorHead error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT
# ═══════════════════════════════════════════════════════════════════════════════

class SensorHeadEnvironmentTool(BaseTool):
    """Read environmental data from SensorHead's BME688 sensor."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_environment",
            description=(
                "Read real-world environmental data from the SensorHead's BME688 sensor. "
                "Returns temperature, humidity, barometric pressure, indoor air quality (IAQ), "
                "CO2 equivalent, and volatile organic compounds (VOC). "
                "The sensor is physically located in the user's room."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _bridge_command(
            context, "sense_environment",
            device_name=params.get("device_name"),
            timeout=15,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CAPTURE (VISUAL + NIGHT)
# ═══════════════════════════════════════════════════════════════════════════════

class SensorHeadCaptureTool(BaseTool):
    """Capture a photo from SensorHead's cameras."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_capture",
            description=(
                "Take a photo using the SensorHead's cameras. "
                "Choose 'visual' for the daylight AI camera (IMX500, 2028x1520) "
                "or 'night' for the wide-angle NoIR camera (IMX708, 2304x1296, IR-sensitive). "
                "Returns a JPEG image of what the SensorHead physically sees."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "camera": {
                        "type": "string",
                        "description": "Which camera to use: 'visual' (daylight) or 'night' (NoIR wide, low-light)",
                        "enum": ["visual", "night"],
                        "default": "visual",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        camera = params.get("camera", "visual")
        action = "capture_visual" if camera == "visual" else "capture_night"
        return await _bridge_command(
            context, action,
            device_name=params.get("device_name"),
            timeout=20,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# THERMAL
# ═══════════════════════════════════════════════════════════════════════════════

class SensorHeadThermalTool(BaseTool):
    """Capture thermal heatmap from SensorHead's MLX90640 sensor."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_thermal",
            description=(
                "Capture a thermal infrared heatmap from the SensorHead's MLX90640 sensor. "
                "Returns a colorized 320x240 JPEG heatmap showing heat signatures. "
                "Useful for detecting people, heat sources, and thermal patterns in the room."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _bridge_command(
            context, "sense_thermal",
            device_name=params.get("device_name"),
            timeout=15,
        )


class SensorHeadThermalDataTool(BaseTool):
    """Read raw thermal statistics from SensorHead's MLX90640."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_thermal_data",
            description=(
                "Read thermal temperature statistics from the SensorHead's infrared sensor. "
                "Returns min, max, and average temperatures in Celsius from the 32x24 pixel "
                "thermal array. Lighter weight than the full heatmap image."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _bridge_command(
            context, "read_thermal",
            device_name=params.get("device_name"),
            timeout=15,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# AI INFERENCE (IMX500 ON-CHIP)
# ═══════════════════════════════════════════════════════════════════════════════

class SensorHeadDetectTool(BaseTool):
    """Run object detection via SensorHead's IMX500 AI camera."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_detect",
            description=(
                "Detect objects in the room using the SensorHead's AI camera (IMX500). "
                "Uses on-chip neural network inference (EfficientDet) to detect 80 COCO classes "
                "including people, furniture, electronics, animals, etc. "
                "Returns bounding boxes, labels, and confidence scores."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "confidence": {
                        "type": "number",
                        "description": "Minimum confidence threshold (0.0-1.0). Default 0.3",
                        "default": 0.3,
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _bridge_command(
            context, "detect_objects",
            params={"confidence": params.get("confidence", 0.3)},
            device_name=params.get("device_name"),
            timeout=20,
        )


class SensorHeadClassifyTool(BaseTool):
    """Classify the scene via SensorHead's IMX500 AI camera."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_classify",
            description=(
                "Classify the current scene using the SensorHead's AI camera (IMX500). "
                "Uses MobileNetV2 to identify the scene from 1000 ImageNet categories. "
                "Returns top-K predictions with confidence scores."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "top_k": {
                        "type": "integer",
                        "description": "Number of top predictions to return. Default 5",
                        "default": 5,
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _bridge_command(
            context, "classify_scene",
            params={"top_k": params.get("top_k", 5)},
            device_name=params.get("device_name"),
            timeout=20,
        )


class SensorHeadPoseTool(BaseTool):
    """Estimate human poses via SensorHead's IMX500 AI camera."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_pose",
            description=(
                "Detect and estimate human body poses using the SensorHead's AI camera (IMX500). "
                "Uses PoseNet to detect 17 body keypoints per person. "
                "Useful for detecting human presence, activity, and gestures."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _bridge_command(
            context, "estimate_poses",
            device_name=params.get("device_name"),
            timeout=20,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════════════════════════

class SensorHeadStatusTool(BaseTool):
    """Get SensorHead hardware status and diagnostics."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_status",
            description=(
                "Get the current status of the SensorHead hardware. "
                "Returns I2C device list, sensor availability, camera status, "
                "memory usage, and firmware version."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _bridge_command(
            context, "get_head_status",
            device_name=params.get("device_name"),
            timeout=10,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SENTINEL GUARDIAN CONTROL
# ═══════════════════════════════════════════════════════════════════════════════


class SensorHeadSentinelArmTool(BaseTool):
    """Arm or disarm the SensorHead Sentinel guardian."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_sentinel_arm",
            description=(
                "Arm or disarm the SensorHead Sentinel — an autonomous thermal motion "
                "detection guardian. When armed, the Sentinel continuously monitors for "
                "heat signatures using the infrared sensor and runs AI confirmation when "
                "motion is detected. Events are logged with thermal snapshots.\n\n"
                "Use action='arm' to begin guarding ('watch the house').\n"
                "Use action='disarm' to stop monitoring ('I'm home, stand down').\n\n"
                "Optionally load a preset before arming:\n"
                "- 'default': Balanced (2°C threshold, 30s cooldown)\n"
                "- 'night_watch': Sensitive overnight (1.5°C, 22:00-07:00 schedule)\n"
                "- 'away_mode': High sensitivity, person-only (1°C, 15s cooldown)\n"
                "- 'pet_watch': Pet-focused (cats/dogs/birds, 60s cooldown)"
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["arm", "disarm"],
                        "description": "Whether to arm (start guarding) or disarm (stop guarding)",
                    },
                    "preset": {
                        "type": "string",
                        "enum": ["default", "night_watch", "away_mode", "pet_watch"],
                        "description": "Load a sensitivity preset before arming. Ignored when disarming.",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": ["action"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        action = params.get("action", "arm")
        device_name = params.get("device_name")

        # Load preset first if arming with one
        if action == "arm" and params.get("preset"):
            preset_result = await _bridge_command(
                context, "sentinel_load_preset",
                params={"preset": params["preset"]},
                device_name=device_name, timeout=10,
            )
            if not preset_result.success:
                return preset_result

        bridge_action = "sentinel_arm" if action == "arm" else "sentinel_disarm"
        return await _bridge_command(
            context, bridge_action,
            device_name=device_name, timeout=10,
        )


class SensorHeadSentinelStatusTool(BaseTool):
    """Check sentinel guardian status."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_sentinel_status",
            description=(
                "Check the current status of the SensorHead Sentinel guardian system. "
                "Returns whether the sentinel is armed, the active configuration "
                "(sensitivity thresholds, cooldown, detection classes), available presets, "
                "and runtime statistics (scans performed, triggers, alerts sent, last alert time)."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _bridge_command(
            context, "sentinel_status",
            device_name=params.get("device_name"), timeout=10,
        )


class SensorHeadSentinelEventsTool(BaseTool):
    """Query the sentinel event timeline from the database."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_sentinel_events",
            description=(
                "Query the Sentinel event timeline — a log of all motion detections, "
                "security alerts, and guardian events from both SensorHead and Pocket Sentinel. "
                "Each event includes thermal delta, detected objects, confidence scores, "
                "and timestamps.\n\n"
                "Use 'hours' to control the lookback window (default 24h).\n"
                "Use 'unacked_only=true' to see only new unacknowledged events.\n"
                "Does NOT return snapshot images — use sensorhead_sentinel_snapshot for those."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "number",
                        "description": "Lookback window in hours. Default 24, max 168.",
                        "default": 24,
                    },
                    "unacked_only": {
                        "type": "boolean",
                        "description": "Only return unacknowledged events. Default false.",
                        "default": False,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max events to return. Default 20, max 100.",
                        "default": 20,
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        from app.database import get_db_context
        from sqlalchemy import text

        hours = max(0.5, min(params.get("hours", 24), 168))
        limit = max(1, min(params.get("limit", 20), 100))
        unacked_only = params.get("unacked_only", False)

        try:
            device_id = await _find_user_device_id(context.user_id, params.get("device_name"))
            if not device_id:
                return ToolResult(success=False, error="No SensorHead device found for your account.")

            async with get_db_context() as db:
                where = """
                    device_id = :did
                    AND (alert_type LIKE 'sentinel_%' OR alert_type LIKE 'pocket_%')
                    AND created_at > NOW() - make_interval(hours => :hours)
                """
                if unacked_only:
                    where += " AND acknowledged = FALSE"

                result = await db.execute(text(f"""
                    SELECT id, alert_type, data, acknowledged, created_at
                    FROM sensor_alerts
                    WHERE {where}
                    ORDER BY created_at DESC
                    LIMIT :limit
                """), {"did": str(device_id), "hours": hours, "limit": limit})

                events = []
                for row in result.mappings().all():
                    raw = row["data"]
                    data = raw if isinstance(raw, dict) else (json.loads(raw) if raw else {})
                    # Strip snapshot to keep response small
                    data.pop("snapshot_b64", None)
                    alert_type = row["alert_type"]
                    is_pocket = alert_type.startswith("pocket_")
                    events.append({
                        "id": str(row["id"]),
                        "type": alert_type.replace("pocket_", "").replace("sentinel_", ""),
                        "source": "pocket" if is_pocket else "sensorhead",
                        "data": data,
                        "acknowledged": row["acknowledged"],
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                        "has_snapshot": bool(data.get("snapshot_b64") or raw.get("snapshot_b64") if isinstance(raw, dict) else False),
                    })

                # Unacked count
                count_result = await db.execute(text("""
                    SELECT COUNT(*) FROM sensor_alerts
                    WHERE device_id = :did
                      AND (alert_type LIKE 'sentinel_%' OR alert_type LIKE 'pocket_%')
                      AND acknowledged = FALSE
                """), {"did": str(device_id)})
                unacked_count = count_result.scalar() or 0

            return ToolResult(
                success=True,
                result={
                    "events": events,
                    "count": len(events),
                    "unacked_count": unacked_count,
                    "hours_queried": hours,
                },
            )
        except Exception as e:
            logger.error(f"Sentinel events query failed: {e}")
            return ToolResult(success=False, error=f"Failed to query events: {e}")


class SensorHeadSentinelSnapshotTool(BaseTool):
    """Retrieve the snapshot image from a sentinel detection event."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_sentinel_snapshot",
            description=(
                "Retrieve the thermal/camera snapshot from a specific Sentinel detection event. "
                "When the Sentinel detects motion, it captures an image at the moment of detection. "
                "Provide an event_id from sensorhead_sentinel_events to view what triggered the alert."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "UUID of the sentinel event. Get this from sensorhead_sentinel_events.",
                    },
                },
                "required": ["event_id"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        from app.database import get_db_context
        from sqlalchemy import text

        event_id = params.get("event_id")
        if not event_id:
            return ToolResult(success=False, error="event_id is required.")

        try:
            device_id = await _find_user_device_id(context.user_id)
            if not device_id:
                return ToolResult(success=False, error="No SensorHead device found for your account.")

            async with get_db_context() as db:
                result = await db.execute(
                    text("SELECT data FROM sensor_alerts WHERE id = :eid AND device_id = :did"),
                    {"eid": event_id, "did": str(device_id)},
                )
                row = result.mappings().first()

            if not row:
                return ToolResult(success=False, error="Event not found.")

            raw = row["data"]
            data = raw if isinstance(raw, dict) else (json.loads(raw) if raw else {})
            snapshot = data.get("snapshot_b64")
            if not snapshot:
                return ToolResult(success=False, error="No snapshot captured for this event.")

            return ToolResult(
                success=True,
                result=snapshot,
                metadata={
                    "data_type": "image_base64",
                    "media_type": "image/jpeg",
                    "caption": f"Sentinel detection snapshot (event {event_id[:8]})",
                },
            )
        except Exception as e:
            logger.error(f"Sentinel snapshot retrieval failed: {e}")
            return ToolResult(success=False, error=f"Failed to retrieve snapshot: {e}")


class SensorHeadSentinelConfigureTool(BaseTool):
    """Tune sentinel detection configuration in real-time."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_sentinel_configure",
            description=(
                "Adjust the Sentinel guardian's detection configuration in real-time. "
                "Changes apply immediately to the running sentinel (hot-reload).\n\n"
                "Configurable parameters:\n"
                "- thermal_threshold: °C delta to trigger (lower = more sensitive, 0.5-5.0)\n"
                "- min_pixels: Minimum thermal pixels above threshold (1-50)\n"
                "- cooldown_seconds: Time between alerts (5-300)\n"
                "- ai_labels: COCO classes to alert on, e.g. ['person', 'cat', 'dog']\n\n"
                "Or load a preset: 'default', 'night_watch', 'away_mode', 'pet_watch'."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "preset": {
                        "type": "string",
                        "description": "Load a named preset instead of individual values.",
                    },
                    "thermal_threshold": {
                        "type": "number",
                        "description": "Temperature delta in °C to trigger. Range 0.5-5.0.",
                    },
                    "min_pixels": {
                        "type": "integer",
                        "description": "Minimum thermal pixels above threshold. Range 1-50.",
                    },
                    "cooldown_seconds": {
                        "type": "integer",
                        "description": "Seconds between alerts. Range 5-300.",
                    },
                    "ai_labels": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "COCO class names for AI filter. e.g. ['person', 'cat']",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        device_name = params.get("device_name")

        if params.get("preset"):
            return await _bridge_command(
                context, "sentinel_load_preset",
                params={"preset": params["preset"]},
                device_name=device_name, timeout=10,
            )

        config = {}
        if "thermal_threshold" in params:
            config["thermal_threshold_c"] = max(0.5, min(params["thermal_threshold"], 5.0))
        if "min_pixels" in params:
            config["min_changed_pixels"] = max(1, min(params["min_pixels"], 50))
        if "cooldown_seconds" in params:
            config["cooldown_s"] = max(5, min(params["cooldown_seconds"], 300))
        if "ai_labels" in params:
            config["ai_labels"] = params["ai_labels"]

        if not config:
            return ToolResult(success=False, error="Provide at least one parameter or a preset name.")

        return await _bridge_command(
            context, "sentinel_configure",
            params=config,
            device_name=device_name, timeout=10,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENTAL INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════


class SensorHeadWeatherTool(BaseTool):
    """Predict weather from barometric pressure trends."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_weather",
            description=(
                "Analyze barometric pressure trends to predict near-term weather changes "
                "and assess indoor comfort. Uses historical sensor telemetry to compute a "
                "pressure slope via linear regression.\n\n"
                "Predictions: stormy (fast drop), rain_likely (moderate drop), "
                "stable, improving (rising), clear (fast rise).\n"
                "Also returns comfort assessment from temperature, humidity, and air quality.\n"
                "Requires at least 30 minutes of telemetry history."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "hours": {
                        "type": "number",
                        "description": "Hours of history to analyze. Default 3, max 24.",
                        "default": 3,
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        from app.database import get_db_context
        from sqlalchemy import text

        hours = max(0.5, min(params.get("hours", 3), 24.0))

        try:
            device_id = await _find_user_device_id(context.user_id, params.get("device_name"))
            if not device_id:
                return ToolResult(success=False, error="No SensorHead device found for your account.")

            async with get_db_context() as db:
                result = await db.execute(text("""
                    SELECT pressure_hpa, temperature_c, humidity_pct, iaq_score,
                           EXTRACT(EPOCH FROM created_at) as epoch
                    FROM sensor_telemetry
                    WHERE device_id = :did
                      AND created_at > NOW() - make_interval(hours => :hours)
                      AND pressure_hpa IS NOT NULL
                    ORDER BY created_at ASC
                    LIMIT 60
                """), {"did": str(device_id), "hours": hours})
                rows = result.mappings().all()

            if len(rows) < 2:
                return ToolResult(success=True, result={
                    "trend": "unknown",
                    "note": "Not enough telemetry data yet. Need at least 30 minutes of readings.",
                    "sample_count": len(rows),
                })

            # Linear regression on pressure
            n = len(rows)
            sum_x = sum(float(r["epoch"]) for r in rows)
            sum_y = sum(float(r["pressure_hpa"]) for r in rows)
            sum_xy = sum(float(r["epoch"]) * float(r["pressure_hpa"]) for r in rows)
            sum_x2 = sum(float(r["epoch"]) ** 2 for r in rows)
            denom = n * sum_x2 - sum_x ** 2
            slope = ((n * sum_xy - sum_x * sum_y) / denom) * 3600 if denom else 0.0

            if slope < -1.5:
                trend = "stormy"
            elif slope < -0.5:
                trend = "rain_likely"
            elif slope <= 0.5:
                trend = "stable"
            elif slope <= 1.5:
                trend = "improving"
            else:
                trend = "clear"

            # Comfort from latest reading
            latest = rows[-1]
            temp = float(latest["temperature_c"]) if latest.get("temperature_c") else None
            hum = float(latest["humidity_pct"]) if latest.get("humidity_pct") else None
            iaq = float(latest["iaq_score"]) if latest.get("iaq_score") else None

            if temp is not None:
                if temp < 18:
                    comfort = "cool"
                elif temp > 26:
                    comfort = "warm"
                elif hum and hum > 60:
                    comfort = "humid"
                elif iaq and iaq > 150:
                    comfort = "stuffy"
                else:
                    comfort = "comfortable"
            else:
                comfort = "unknown"

            return ToolResult(success=True, result={
                "trend": trend,
                "pressure_slope_hpa_hr": round(slope, 3),
                "comfort": comfort,
                "latest_pressure_hpa": round(float(latest["pressure_hpa"]), 1),
                "latest_temperature_c": round(temp, 1) if temp else None,
                "latest_humidity_pct": round(hum, 0) if hum else None,
                "latest_iaq": round(iaq, 0) if iaq else None,
                "sample_count": n,
            })
        except Exception as e:
            logger.error(f"Weather tool failed: {e}")
            return ToolResult(success=False, error=f"Weather analysis failed: {e}")


class SensorHeadAirQualityTool(BaseTool):
    """Comprehensive air quality assessment with recommendations."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_air_quality",
            description=(
                "Provide a comprehensive indoor air quality assessment with actionable advice. "
                "Reads live sensor data and interprets it:\n\n"
                "- IAQ rating: Excellent/Good/Moderate/Unhealthy/Hazardous (0-500 scale)\n"
                "- CO2 level: Fresh/Normal/Stuffy/Poor/Dangerous\n"
                "- VOC level: Clean/Normal/Elevated/High\n"
                "- Humidity comfort: Dry/Comfortable/Humid\n"
                "- Actionable recommendation: 'Open a window', 'Air is great', etc.\n\n"
                "Use this when the user asks about air quality, ventilation, or comfort."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        # Live reading from bridge
        live = await _bridge_command(
            context, "sense_environment",
            device_name=params.get("device_name"), timeout=15,
        )
        if not live.success:
            return live

        data = live.result if isinstance(live.result, dict) else {}
        iaq = data.get("iaq")
        co2 = data.get("co2_equivalent_ppm")
        voc = data.get("breath_voc_ppm")
        hum = data.get("humidity_pct")
        temp = data.get("temperature_c")

        # Classify IAQ (0-500 BSEC scale)
        if iaq is not None:
            if iaq <= 50:
                iaq_rating = "Excellent"
            elif iaq <= 100:
                iaq_rating = "Good"
            elif iaq <= 150:
                iaq_rating = "Moderate"
            elif iaq <= 200:
                iaq_rating = "Unhealthy"
            elif iaq <= 300:
                iaq_rating = "Very Unhealthy"
            else:
                iaq_rating = "Hazardous"
        else:
            iaq_rating = "Unknown"

        # Classify CO2
        if co2 is not None:
            if co2 < 600:
                co2_level = "Fresh"
            elif co2 < 1000:
                co2_level = "Normal"
            elif co2 < 1500:
                co2_level = "Stuffy"
            elif co2 < 2500:
                co2_level = "Poor"
            else:
                co2_level = "Dangerous"
        else:
            co2_level = "Unknown"

        # Classify VOC
        if voc is not None:
            if voc < 0.5:
                voc_level = "Clean"
            elif voc < 1.0:
                voc_level = "Normal"
            elif voc < 3.0:
                voc_level = "Elevated"
            else:
                voc_level = "High"
        else:
            voc_level = "Unknown"

        # Classify humidity
        if hum is not None:
            if hum < 30:
                humidity = "Dry"
            elif hum <= 60:
                humidity = "Comfortable"
            else:
                humidity = "Humid"
        else:
            humidity = "Unknown"

        # Generate recommendation
        issues = []
        if co2 is not None and co2 >= 1000:
            issues.append("CO2 is elevated")
        if iaq is not None and iaq > 150:
            issues.append("air quality is poor")
        if voc is not None and voc >= 1.0:
            issues.append("VOCs are elevated")
        if hum is not None and hum > 65:
            issues.append("humidity is high")
        if hum is not None and hum < 25:
            issues.append("air is very dry")

        if not issues:
            recommendation = "Air quality is great — no action needed."
        elif "CO2 is elevated" in issues or "air quality is poor" in issues:
            recommendation = "Consider opening a window to improve ventilation."
        elif "humidity is high" in issues:
            recommendation = "Humidity is high — consider a dehumidifier or opening a window."
        elif "air is very dry" in issues:
            recommendation = "Air is very dry — consider a humidifier for comfort."
        else:
            recommendation = f"Note: {', '.join(issues)}. Monitor and ventilate if needed."

        return ToolResult(success=True, result={
            "iaq_score": round(iaq, 0) if iaq else None,
            "iaq_rating": iaq_rating,
            "iaq_accuracy": data.get("iaq_accuracy"),
            "co2_ppm": round(co2, 0) if co2 else None,
            "co2_level": co2_level,
            "voc_ppm": round(voc, 2) if voc else None,
            "voc_level": voc_level,
            "humidity_pct": round(hum, 1) if hum else None,
            "humidity_comfort": humidity,
            "temperature_c": round(temp, 1) if temp else None,
            "recommendation": recommendation,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# VOICE OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════


class SensorHeadSpeakTool(BaseTool):
    """Speak text aloud through the SensorHead's speaker."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_speak",
            description=(
                "Speak text aloud through the SensorHead's connected speaker using "
                "text-to-speech. The voice comes from the physical hardware in the user's room.\n\n"
                "This gives you a physical voice — greet someone entering the room, "
                "announce alerts, narrate observations, or respond to voice commands.\n"
                "Keep text under 500 characters for natural speech cadence."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to speak aloud. Keep under 500 characters.",
                    },
                    "speed": {
                        "type": "number",
                        "description": "Speech speed: 0.5 (slow) to 2.0 (fast). Default 1.0.",
                        "default": 1.0,
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": ["text"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        text_input = params.get("text", "")
        if not text_input:
            return ToolResult(success=False, error="No text provided.")
        if len(text_input) > 500:
            text_input = text_input[:500]

        speed = max(0.5, min(params.get("speed", 1.0), 2.0))

        return await _bridge_command(
            context, "tts_speak",
            params={"text": text_input, "voice": "system", "speed": speed},
            device_name=params.get("device_name"),
            timeout=15,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# COMPOSITE MULTI-SENSOR INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════


class SensorHeadSceneReportTool(BaseTool):
    """Full situational awareness from multiple sensors."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_scene_report",
            description=(
                "Generate a comprehensive scene report by combining multiple SensorHead sensors "
                "simultaneously. Captures a visual photo, runs AI object detection, reads thermal "
                "data, and samples the environment — returning everything for a complete picture.\n\n"
                "This is the 'look around and tell me everything' tool. Instead of calling "
                "4 separate tools, this combines them into a single observation.\n\n"
                "Returns: visual photo, object detections (people/furniture/pets), "
                "thermal summary (min/max/avg temperature), and environment snapshot."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "include_photo": {
                        "type": "boolean",
                        "description": "Include a visual photo. Default true.",
                        "default": True,
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        device_name = params.get("device_name")
        include_photo = params.get("include_photo", True)

        # Thermal + environment can run in parallel with each other
        # IMX500 capture and detect must be sequential (same camera)
        thermal_task = _bridge_command(context, "read_thermal", device_name=device_name, timeout=15)
        env_task = _bridge_command(context, "sense_environment", device_name=device_name, timeout=15)

        # Start parallel tasks
        thermal_result, env_result = await asyncio.gather(
            thermal_task, env_task, return_exceptions=True,
        )

        # Sequential IMX500 operations
        photo_data = None
        if include_photo:
            photo_result = await _bridge_command(
                context, "capture_visual", device_name=device_name, timeout=20,
            )
            if photo_result.success:
                photo_data = photo_result.result

        detect_result = await _bridge_command(
            context, "detect_objects",
            params={"confidence": 0.3},
            device_name=device_name, timeout=20,
        )

        # Assemble report
        report = {}

        if isinstance(detect_result, ToolResult) and detect_result.success:
            detections = detect_result.result
            report["detections"] = detections if isinstance(detections, dict) else {}
        else:
            report["detections"] = {"error": "Detection unavailable"}

        if isinstance(thermal_result, ToolResult) and thermal_result.success:
            thermal = thermal_result.result if isinstance(thermal_result.result, dict) else {}
            report["thermal"] = {
                "min_c": thermal.get("min_c"),
                "max_c": thermal.get("max_c"),
                "avg_c": thermal.get("avg_c"),
            }
        else:
            report["thermal"] = {"error": "Thermal unavailable"}

        if isinstance(env_result, ToolResult) and env_result.success:
            env = env_result.result if isinstance(env_result.result, dict) else {}
            report["environment"] = {
                "temperature_c": env.get("temperature_c"),
                "humidity_pct": env.get("humidity_pct"),
                "iaq": env.get("iaq"),
                "air_quality": env.get("air_quality"),
                "co2_ppm": env.get("co2_equivalent_ppm"),
            }
        else:
            report["environment"] = {"error": "Environment unavailable"}

        # Return photo as primary content if available
        if photo_data:
            return ToolResult(
                success=True,
                result=photo_data,
                metadata={
                    "data_type": "image_base64",
                    "media_type": "image/jpeg",
                    "caption": json.dumps(report),
                },
            )

        return ToolResult(success=True, result=report)


class SensorHeadNightVisionTool(BaseTool):
    """Night vision check with thermal context."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="sensorhead_night_vision",
            description=(
                "Capture a night vision image using the SensorHead's NoIR infrared-sensitive "
                "camera, combined with thermal sensor data for heat signature context. "
                "The NoIR camera can see in low-light and complete darkness with IR illumination.\n\n"
                "Ideal for checking rooms at night — you get both what the camera sees and "
                "where heat sources are. Returns the NoIR image plus thermal min/max/avg temperatures."
            ),
            category=ToolCategory.SENSORHEAD,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple SensorHeads",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        device_name = params.get("device_name")

        # Parallel: NoIR capture + thermal read (different hardware, no contention)
        noir_task = _bridge_command(context, "capture_night_cropped", device_name=device_name, timeout=20)
        thermal_task = _bridge_command(context, "read_thermal", device_name=device_name, timeout=15)

        noir_result, thermal_result = await asyncio.gather(
            noir_task, thermal_task, return_exceptions=True,
        )

        if isinstance(noir_result, ToolResult) and not noir_result.success:
            return noir_result
        if isinstance(noir_result, Exception):
            return ToolResult(success=False, error=f"Night camera failed: {noir_result}")

        # Build thermal context for caption
        thermal_info = "Thermal data unavailable"
        if isinstance(thermal_result, ToolResult) and thermal_result.success:
            t = thermal_result.result if isinstance(thermal_result.result, dict) else {}
            thermal_info = (
                f"Thermal: min {t.get('min_c', '?')}°C, "
                f"max {t.get('max_c', '?')}°C, "
                f"avg {t.get('avg_c', '?')}°C"
            )

        return ToolResult(
            success=True,
            result=noir_result.result,
            metadata={
                "data_type": "image_base64",
                "media_type": "image/jpeg",
                "caption": f"Night vision capture. {thermal_info}",
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


async def _find_user_device_id(user_id, device_name=None):
    """Find a user's SensorHead device_id from the database."""
    from app.database import get_db_context
    from sqlalchemy import text

    try:
        async with get_db_context() as db:
            if device_name:
                result = await db.execute(
                    text("SELECT id FROM devices WHERE user_id = :uid AND device_name = :name LIMIT 1"),
                    {"uid": str(user_id), "name": device_name},
                )
            else:
                result = await db.execute(
                    text("SELECT id FROM devices WHERE user_id = :uid LIMIT 1"),
                    {"uid": str(user_id)},
                )
            row = result.scalar_one_or_none()
            return row
    except Exception as e:
        logger.error(f"Device lookup failed: {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

# Register all SensorHead tools — 8 original + 10 new
registry.register(SensorHeadEnvironmentTool())
registry.register(SensorHeadCaptureTool())
registry.register(SensorHeadThermalTool())
registry.register(SensorHeadThermalDataTool())
registry.register(SensorHeadDetectTool())
registry.register(SensorHeadClassifyTool())
registry.register(SensorHeadPoseTool())
registry.register(SensorHeadStatusTool())

# Sentinel Guardian
registry.register(SensorHeadSentinelArmTool())
registry.register(SensorHeadSentinelStatusTool())
registry.register(SensorHeadSentinelEventsTool())
registry.register(SensorHeadSentinelSnapshotTool())
registry.register(SensorHeadSentinelConfigureTool())

# Environmental Intelligence
registry.register(SensorHeadWeatherTool())
registry.register(SensorHeadAirQualityTool())

# Voice
registry.register(SensorHeadSpeakTool())

# Composite Multi-Sensor
registry.register(SensorHeadSceneReportTool())
registry.register(SensorHeadNightVisionTool())
