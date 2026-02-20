"""
EEG / BCI Proxy Tools

Tools that route through the Bridge WebSocket tunnel to connected
EEG headset hardware (OpenBCI Cyton/Ganglion). Gives AI agents the
ability to perceive human brain states — emotion, attention, engagement,
and musical chills — in real time.

"Brainwaves for the mind"
"""

import asyncio
import logging

from . import registry
from .base import BaseTool, ToolSchema, ToolResult, ToolContext, ToolCategory

logger = logging.getLogger(__name__)


async def _eeg_bridge_command(
    context: ToolContext,
    action: str,
    params: dict | None = None,
    timeout: float = 30.0,
    device_name: str | None = None,
) -> ToolResult:
    """
    Common helper: find user's EEG headset and send a command.

    Returns ToolResult with the response data, or an error if
    the device isn't connected or the command fails.
    """
    from app.services.bridge_manager import get_bridge_manager

    manager = get_bridge_manager()
    conn = manager.find_device_for_user(
        context.user_id, device_name, device_type="eeg_headset"
    )

    if not conn:
        return ToolResult(
            success=False,
            error=(
                "No EEG headset connected. "
                "Check that your OpenBCI bridge client is running and connected to the cloud."
            ),
        )

    try:
        result = await manager.send_command(
            conn.device_id, action, params or {}, timeout=timeout
        )
        metadata = {
            "device_name": conn.device_name,
            "data_type": result.get("data_type", "json"),
            "device_duration_ms": result.get("duration_ms", 0),
        }

        return ToolResult(
            success=True,
            result=result.get("data"),
            metadata=metadata,
        )
    except asyncio.TimeoutError:
        return ToolResult(
            success=False,
            error=f"EEG headset did not respond within {timeout}s. The device may be busy or offline.",
        )
    except ConnectionError as e:
        return ToolResult(success=False, error=str(e))
    except RuntimeError as e:
        return ToolResult(success=False, error=f"EEG headset error: {e}")


# ============================================================================
# CONNECTION
# ============================================================================

class EEGConnectTool(BaseTool):
    """Connect to an OpenBCI EEG board via the bridge."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_connect",
            description=(
                "Connect to an OpenBCI EEG board (Cyton 8-channel, Ganglion 4-channel, "
                "or synthetic for testing). The board must be physically connected to the "
                "machine running the EEG bridge client. Use board_type='synthetic' with "
                "empty serial_port for testing without hardware."
            ),
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "serial_port": {
                        "type": "string",
                        "description": (
                            "Serial port (e.g., '/dev/ttyUSB0' on Linux, 'COM3' on Windows). "
                            "Use empty string '' for synthetic board."
                        ),
                    },
                    "board_type": {
                        "type": "string",
                        "enum": ["cyton", "ganglion", "synthetic"],
                        "default": "cyton",
                        "description": "Board type: 'cyton' (8-ch), 'ganglion' (4-ch), or 'synthetic' (testing)",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": ["serial_port"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context,
            "eeg_connect",
            {"serial_port": params["serial_port"], "board_type": params.get("board_type", "cyton")},
            device_name=params.get("device_name"),
            timeout=15,
        )


class EEGDisconnectTool(BaseTool):
    """Disconnect from the EEG board."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_disconnect",
            description="Disconnect from the EEG board and release hardware resources.",
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context, "eeg_disconnect",
            device_name=params.get("device_name"),
            timeout=10,
        )


# ============================================================================
# STREAMING
# ============================================================================

class EEGStreamStartTool(BaseTool):
    """Start EEG streaming and emotional response recording."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_stream_start",
            description=(
                "Start EEG streaming and recording for a music listening session. "
                "Continuously records emotional response data (valence, arousal, attention, "
                "engagement) and detects musical chills. The session runs until eeg_stream_stop "
                "is called."
            ),
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "session_name": {
                        "type": "string",
                        "description": "Name for this listening session",
                    },
                    "track_id": {
                        "type": "string",
                        "description": "ID of the track being listened to (from music_generate)",
                    },
                    "track_title": {
                        "type": "string",
                        "description": "Title of the track",
                    },
                    "listener_name": {
                        "type": "string",
                        "default": "Listener",
                        "description": "Name of the listener",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": ["session_name"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context,
            "eeg_stream_start",
            {
                "session_name": params["session_name"],
                "track_id": params.get("track_id", ""),
                "track_title": params.get("track_title", ""),
                "listener_name": params.get("listener_name", "Listener"),
            },
            device_name=params.get("device_name"),
            timeout=15,
        )


class EEGStreamStopTool(BaseTool):
    """Stop EEG streaming and generate felt experience."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_stream_stop",
            description=(
                "Stop EEG streaming and generate the AI-readable 'felt experience' format. "
                "Returns emotional summary with valence/arousal/attention/engagement stats, "
                "chills count, and a natural language narrative of the listening experience."
            ),
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "generate_experience": {
                        "type": "boolean",
                        "default": True,
                        "description": "Generate and save the felt experience format",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context,
            "eeg_stream_stop",
            {"generate_experience": params.get("generate_experience", True)},
            device_name=params.get("device_name"),
            timeout=30,
        )


# ============================================================================
# REAL-TIME EMOTION
# ============================================================================

class EEGRealtimeEmotionTool(BaseTool):
    """Get current real-time emotional state."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_realtime_emotion",
            description=(
                "Get current real-time emotional state during active EEG streaming. "
                "Returns valence (-1 to +1), arousal (0-1), attention (0-1), engagement (0-1), "
                "and chills detection. Must call eeg_stream_start first."
            ),
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context, "eeg_realtime_emotion",
            device_name=params.get("device_name"),
            timeout=10,
        )


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================

class EEGExperienceGetTool(BaseTool):
    """Retrieve felt experience from a recorded session."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_experience_get",
            description=(
                "Retrieve the felt experience from a recorded listening session. "
                "This is how AI agents 'feel' what the human experienced during music "
                "listening. Returns emotional data at the requested detail level."
            ),
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "The session ID to retrieve (e.g., 'listen_20260114_143022')",
                    },
                    "detail_level": {
                        "type": "string",
                        "enum": ["summary", "full", "narrative"],
                        "default": "full",
                        "description": "Detail level: 'summary' (stats + narrative), 'full' (all data), 'narrative' (just text)",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": ["session_id"],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context,
            "eeg_experience_get",
            {
                "session_id": params["session_id"],
                "detail_level": params.get("detail_level", "full"),
            },
            device_name=params.get("device_name"),
            timeout=15,
        )


class EEGListSessionsTool(BaseTool):
    """List available recorded EEG sessions."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_list_sessions",
            description="List available recorded EEG listening sessions stored on the bridge device.",
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of sessions to return",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context,
            "eeg_list_sessions",
            {"limit": params.get("limit", 10)},
            device_name=params.get("device_name"),
            timeout=10,
        )


# ============================================================================
# CALIBRATION
# ============================================================================

class EEGCalibrateBaselineTool(BaseTool):
    """Prepare for baseline EEG calibration."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_calibrate_baseline",
            description=(
                "Prepare for baseline EEG calibration. Improves emotion detection accuracy "
                "by recording personal baseline patterns (eyes open + eyes closed)."
            ),
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "listener_name": {
                        "type": "string",
                        "default": "Listener",
                        "description": "Name of the person being calibrated",
                    },
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context,
            "eeg_calibrate_baseline",
            {"listener_name": params.get("listener_name", "Listener")},
            device_name=params.get("device_name"),
            timeout=10,
        )


# ============================================================================
# STATUS
# ============================================================================

class EEGStatusTool(BaseTool):
    """Get EEG board connection and streaming status."""

    @property
    def schema(self) -> ToolSchema:
        return ToolSchema(
            name="eeg_status",
            description=(
                "Get current EEG board connection status, streaming state, board info "
                "(channels, sampling rate), and bridge connection health."
            ),
            category=ToolCategory.EEG,
            input_schema={
                "type": "object",
                "properties": {
                    "device_name": {
                        "type": "string",
                        "description": "Device name if user has multiple EEG headsets",
                    },
                },
                "required": [],
            },
        )

    async def execute(self, params: dict, context: ToolContext) -> ToolResult:
        return await _eeg_bridge_command(
            context, "eeg_status",
            device_name=params.get("device_name"),
            timeout=10,
        )


# ============================================================================
# REGISTER ALL EEG TOOLS
# ============================================================================

# Connection
registry.register(EEGConnectTool())
registry.register(EEGDisconnectTool())

# Streaming
registry.register(EEGStreamStartTool())
registry.register(EEGStreamStopTool())

# Real-time
registry.register(EEGRealtimeEmotionTool())

# Sessions
registry.register(EEGExperienceGetTool())
registry.register(EEGListSessionsTool())

# Calibration
registry.register(EEGCalibrateBaselineTool())

# Status
registry.register(EEGStatusTool())
