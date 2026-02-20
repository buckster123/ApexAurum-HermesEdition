"""
Bridge Connection Manager

Singleton managing active WebSocket tunnels to SensorHead devices.
Commands flow cloud→device, responses and telemetry flow device→cloud.

"The bridge between the digital and the physical"
"""

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class BridgeConnection:
    """An active SensorHead WebSocket connection."""
    device_id: UUID
    user_id: UUID
    websocket: WebSocket
    connected_at: float = field(default_factory=time.time)
    last_telemetry: Optional[dict] = None
    last_telemetry_at: Optional[float] = None
    device_name: Optional[str] = None
    device_type: str = "sensor_head"


class BridgeConnectionManager:
    """
    Manages active WebSocket tunnels to SensorHead devices.

    Singleton pattern matching ToolRegistry and VillageBroadcaster.
    """

    _instance: Optional["BridgeConnectionManager"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._connections: dict[UUID, BridgeConnection] = {}
            cls._instance._pending: dict[str, asyncio.Future] = {}
            cls._instance._telemetry_rate: dict[UUID, float] = {}
        return cls._instance

    def register(
        self,
        device_id: UUID,
        user_id: UUID,
        websocket: WebSocket,
        device_name: Optional[str] = None,
        device_type: str = "sensor_head",
    ) -> BridgeConnection:
        """Register a new bridge device connection."""
        conn = BridgeConnection(
            device_id=device_id,
            user_id=user_id,
            websocket=websocket,
            device_name=device_name,
            device_type=device_type,
        )
        self._connections[device_id] = conn
        logger.info(
            f"SensorHead connected: {device_name or device_id} "
            f"(user={user_id}, total={len(self._connections)})"
        )
        return conn

    def unregister(self, device_id: UUID) -> None:
        """Remove a SensorHead connection."""
        conn = self._connections.pop(device_id, None)
        if conn:
            logger.info(
                f"SensorHead disconnected: {conn.device_name or device_id} "
                f"(total={len(self._connections)})"
            )
            # Cancel any pending commands for this device
            to_cancel = [
                k for k, v in self._pending.items()
                if k.startswith(str(device_id))
            ]
            for k in to_cancel:
                fut = self._pending.pop(k, None)
                if fut and not fut.done():
                    fut.set_exception(ConnectionError("SensorHead disconnected"))

    def is_connected(self, device_id: UUID) -> bool:
        """Check if a specific device is online."""
        return device_id in self._connections

    def get_connection(self, device_id: UUID) -> Optional[BridgeConnection]:
        """Get a specific connection."""
        return self._connections.get(device_id)

    def get_connected_devices(self, user_id: UUID) -> list[BridgeConnection]:
        """List all connected SensorHeads for a user."""
        return [
            c for c in self._connections.values()
            if c.user_id == user_id
        ]

    def find_device_for_user(
        self,
        user_id: UUID,
        device_name: Optional[str] = None,
        device_type: Optional[str] = None,
    ) -> Optional[BridgeConnection]:
        """Find a connected bridge device for a user, optionally by name or type."""
        devices = self.get_connected_devices(user_id)
        if not devices:
            return None
        if device_type:
            devices = [d for d in devices if d.device_type == device_type]
            if not devices:
                return None
        if device_name:
            for d in devices:
                if d.device_name and d.device_name.lower() == device_name.lower():
                    return d
        return devices[0]  # Default to first matching device

    async def send_command(
        self,
        device_id: UUID,
        action: str,
        params: Optional[dict] = None,
        timeout: float = 30.0,
    ) -> Any:
        """
        Send a command to a SensorHead and await the response.

        Creates a Future keyed by command ID, sends the command JSON,
        and awaits the Future with a timeout. The WebSocket receive
        loop resolves the Future when a matching response arrives.

        Raises:
            ConnectionError: Device not connected
            asyncio.TimeoutError: Device didn't respond in time
            RuntimeError: Device returned an error
        """
        conn = self._connections.get(device_id)
        if not conn:
            raise ConnectionError(f"SensorHead {device_id} not connected")

        cmd_id = f"{device_id}_{uuid.uuid4().hex[:8]}"
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[cmd_id] = future

        command = {
            "type": "command",
            "id": cmd_id,
            "action": action,
            "params": params or {},
            "timeout_ms": int(timeout * 1000),
        }

        try:
            await conn.websocket.send_text(json.dumps(command))
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Command timeout: {action} on {device_id}")
            raise
        finally:
            self._pending.pop(cmd_id, None)

    def resolve_command(self, cmd_id: str, response: dict) -> bool:
        """
        Resolve a pending command Future with its response.

        Called by the WebSocket receive loop when a response arrives.
        Returns True if the command was found and resolved.
        """
        future = self._pending.get(cmd_id)
        if not future or future.done():
            return False

        if response.get("success"):
            future.set_result({
                "data": response.get("data"),
                "data_type": response.get("data_type", "json"),
                "duration_ms": response.get("duration_ms", 0),
            })
        else:
            future.set_exception(
                RuntimeError(response.get("error", "Unknown device error"))
            )
        return True

    def update_telemetry(
        self,
        device_id: UUID,
        readings: dict,
        timestamp: Optional[float] = None,
    ) -> bool:
        """
        Cache latest telemetry from a SensorHead.

        Rate-limited to 1 update per 10 seconds per device.
        Returns True if the update was accepted.
        """
        now = time.time()
        last = self._telemetry_rate.get(device_id, 0)
        if now - last < 10:
            return False  # Rate limited

        conn = self._connections.get(device_id)
        if conn:
            conn.last_telemetry = readings
            conn.last_telemetry_at = timestamp or now
            self._telemetry_rate[device_id] = now
            return True
        return False

    def get_telemetry(self, device_id: UUID) -> Optional[dict]:
        """Get cached telemetry for a device."""
        conn = self._connections.get(device_id)
        if conn and conn.last_telemetry:
            return {
                "readings": conn.last_telemetry,
                "timestamp": conn.last_telemetry_at,
                "age_s": round(time.time() - (conn.last_telemetry_at or 0), 1),
            }
        return None

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    def status(self) -> dict:
        """Full manager status."""
        return {
            "connected_devices": self.connection_count,
            "pending_commands": len(self._pending),
            "devices": [
                {
                    "device_id": str(c.device_id),
                    "user_id": str(c.user_id),
                    "device_name": c.device_name,
                    "connected_at": c.connected_at,
                    "has_telemetry": c.last_telemetry is not None,
                }
                for c in self._connections.values()
            ],
        }


# Module-level singleton accessor
def get_bridge_manager() -> BridgeConnectionManager:
    """Get the global bridge connection manager."""
    return BridgeConnectionManager()
