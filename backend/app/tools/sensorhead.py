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
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

# Register all SensorHead tools
registry.register(SensorHeadEnvironmentTool())
registry.register(SensorHeadCaptureTool())
registry.register(SensorHeadThermalTool())
registry.register(SensorHeadThermalDataTool())
registry.register(SensorHeadDetectTool())
registry.register(SensorHeadClassifyTool())
registry.register(SensorHeadPoseTool())
registry.register(SensorHeadStatusTool())
