#!/usr/bin/env python3
"""
EEG Bridge Client — OpenBCI to ApexAurum Cloud

Connects local OpenBCI hardware to the ApexAurum Cloud platform
via WebSocket tunnel. Handles EEG commands from Cloud AI agents,
processes brain signals locally, and streams emotion data back.

Usage:
    # Set up environment variables
    export EEG_BRIDGE_TOKEN="apex_dev_your_token_here"
    export EEG_BRIDGE_URL="wss://backend-production-507c.up.railway.app/ws/bridge"

    # Run from the ApexAurum-Local directory (where core/eeg/ lives)
    python eeg_bridge.py

    # Or specify options directly
    python eeg_bridge.py --token apex_dev_xxx --url wss://...

Requirements:
    pip install websockets brainflow numpy scipy

The bridge client must be run from a directory containing core/eeg/
(i.e., the ApexAurum-Local project root) or with PYTHONPATH set to
include the core EEG modules.
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Any, Dict, Optional

# Attempt to import websockets
try:
    import websockets
    import websockets.exceptions
except ImportError:
    print("ERROR: websockets package required. Install: pip install websockets")
    sys.exit(1)

# Attempt to import core EEG modules
try:
    from core.eeg.connection import EEGConnection
    from core.eeg.processor import EEGProcessor
    from core.eeg.experience import EmotionMapper, ListeningSession, MomentExperience
except ImportError:
    print("ERROR: Cannot find core.eeg modules.")
    print("Run this script from the ApexAurum project root directory,")
    print("or set PYTHONPATH to include the directory containing core/eeg/")
    sys.exit(1)

# ─── Configuration ──────────────────────────────────────────────────

DEFAULT_URL = "wss://backend-production-507c.up.railway.app/ws/bridge"
RECONNECT_DELAY = 5  # seconds between reconnection attempts
TELEMETRY_INTERVAL = 2.0  # seconds between emotion telemetry pushes
PING_INTERVAL = 30  # seconds between keepalive pings
SESSION_DIR = "eeg_sessions"

# ─── Logging ────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("eeg_bridge")

# ─── Color output ───────────────────────────────────────────────────

GOLD = "\033[33m"
GREEN = "\033[32m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"
RESET = "\033[0m"
BOLD = "\033[1m"


def info(msg: str):
    logger.info(f"{CYAN}{msg}{RESET}")


def success(msg: str):
    logger.info(f"{GREEN}{msg}{RESET}")


def error(msg: str):
    logger.error(f"{RED}{msg}{RESET}")


# ─── EEG Manager ────────────────────────────────────────────────────

class EEGManager:
    """
    Manages local EEG hardware and signal processing.
    Wraps the core/eeg/ modules for bridge command handling.
    """

    def __init__(self):
        self.connection = EEGConnection()
        self.processor = EEGProcessor()
        self.mapper = EmotionMapper()
        self.current_session: Optional[Dict] = None
        self.session_start_time: Optional[float] = None
        self.session_moments: list = []
        self._stream_thread: Optional[threading.Thread] = None

    def handle_command(self, action: str, params: dict) -> dict:
        """
        Handle an incoming command from the Cloud.
        Returns a response dict with success/data or error.
        """
        handler = getattr(self, f"_cmd_{action}", None)
        if not handler:
            return {"success": False, "error": f"Unknown action: {action}"}

        try:
            start = time.time()
            result = handler(params)
            duration_ms = int((time.time() - start) * 1000)
            return {
                "success": True,
                "data": result,
                "data_type": "json",
                "duration_ms": duration_ms,
            }
        except Exception as e:
            logger.exception(f"Command error: {action}")
            return {"success": False, "error": str(e)}

    def _cmd_eeg_connect(self, params: dict) -> dict:
        serial_port = params.get("serial_port", "")
        board_type = params.get("board_type", "cyton")
        result = self.connection.connect(serial_port, board_type)
        return result

    def _cmd_eeg_disconnect(self, params: dict) -> dict:
        return self.connection.disconnect()

    def _cmd_eeg_stream_start(self, params: dict) -> dict:
        if not self.connection.board:
            return {"success": False, "error": "Not connected. Call eeg_connect first."}

        result = self.connection.start_stream()
        if not result.get("success"):
            return result

        session_name = params.get("session_name", "unnamed")
        session_id = f"listen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_moments = []

        self.current_session = {
            "id": session_id,
            "name": session_name,
            "track_id": params.get("track_id", ""),
            "track_title": params.get("track_title", session_name),
            "listener": params.get("listener_name", "Listener"),
            "start_time": datetime.now(),
        }
        self.session_start_time = time.time()

        # Start background processing thread
        def process_stream():
            conn = self.connection
            proc = self.processor
            mapper = self.mapper
            start_time = time.time()

            while conn.is_streaming:
                try:
                    data = conn.get_current_data(conn.sampling_rate)
                    if data is not None and data.shape[1] >= conn.sampling_rate // 2:
                        processed = proc.process_window(
                            data, conn.eeg_channels, conn.channel_names
                        )
                        elapsed_ms = int((time.time() - start_time) * 1000)
                        moment = mapper.process_moment(
                            processed["band_powers"],
                            timestamp_ms=elapsed_ms,
                            track_position=self._format_timestamp(elapsed_ms),
                        )
                        self.session_moments.append(moment)
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"Stream processing: {e}")
                    time.sleep(0.5)

        self._stream_thread = threading.Thread(target=process_stream, daemon=True)
        self._stream_thread.start()

        return {
            "success": True,
            "session_id": session_id,
            "track_id": params.get("track_id", ""),
            "track_title": params.get("track_title", session_name),
            "listener": params.get("listener_name", "Listener"),
            "message": f"Streaming started for session: {session_name}",
            "board_info": self.connection.get_status(),
        }

    def _cmd_eeg_stream_stop(self, params: dict) -> dict:
        self.connection.stop_stream()
        session = self.current_session

        if not session:
            return {"success": True, "message": "Streaming stopped (no active session)"}

        duration_ms = 0
        if self.session_start_time:
            duration_ms = int((time.time() - self.session_start_time) * 1000)

        result = {
            "success": True,
            "session_id": session["id"],
            "duration_ms": duration_ms,
            "duration_formatted": self._format_timestamp(duration_ms),
            "moments_recorded": len(self.session_moments),
        }

        generate = params.get("generate_experience", True)
        if generate and self.session_moments:
            listening_session = ListeningSession(
                session_id=session["id"],
                track_id=session["track_id"],
                track_title=session["track_title"],
                listener=session["listener"],
                duration_ms=duration_ms,
                moments=self.session_moments,
            )

            # Save locally
            os.makedirs(SESSION_DIR, exist_ok=True)
            filepath = f"{SESSION_DIR}/{session['id']}.json"
            listening_session.save_to_file(filepath)

            experience_data = listening_session.to_dict()
            result["experience"] = experience_data
            result["narrative"] = experience_data.get("experience_narrative", "")
            result["summary"] = experience_data.get("summary", {})
            result["saved_to"] = filepath

        self.current_session = None
        self.session_start_time = None
        self.session_moments = []

        return result

    def _cmd_eeg_realtime_emotion(self, params: dict) -> dict:
        if not self.connection.is_streaming:
            return {"success": False, "error": "Not streaming. Call eeg_stream_start first."}

        conn = self.connection
        data = conn.get_current_data(conn.sampling_rate)

        if data is None or data.shape[1] < conn.sampling_rate // 2:
            return {"success": False, "error": "Insufficient data. Wait a moment."}

        processed = self.processor.process_window(
            data, conn.eeg_channels, conn.channel_names
        )
        moment = self.mapper.process_moment(
            processed["band_powers"],
            timestamp_ms=0,
            track_position="live",
            include_raw=False,
        )

        return {
            "success": True,
            "valence": round(moment.valence, 3),
            "arousal": round(moment.arousal, 3),
            "attention": round(moment.attention, 3),
            "engagement": round(moment.engagement, 3),
            "possible_chills": moment.possible_chills,
            "emotional_peak": moment.emotional_peak,
            "interpretation": self._interpret_emotion(moment.valence, moment.arousal),
        }

    def _cmd_eeg_experience_get(self, params: dict) -> dict:
        session_id = params.get("session_id", "")
        detail_level = params.get("detail_level", "full")
        filepath = f"{SESSION_DIR}/{session_id}.json"

        if not os.path.exists(filepath):
            available = []
            if os.path.exists(SESSION_DIR):
                available = [
                    f.replace(".json", "")
                    for f in os.listdir(SESSION_DIR)
                    if f.endswith(".json")
                ]
            return {
                "success": False,
                "error": f"Session not found: {session_id}",
                "available_sessions": available[:10],
            }

        with open(filepath) as f:
            data = json.load(f)

        if detail_level == "summary":
            return {
                "success": True,
                "session_id": session_id,
                "track_title": data.get("track_title", ""),
                "listener": data.get("listener", ""),
                "duration_ms": data.get("duration_ms", 0),
                "summary": data.get("summary", {}),
                "narrative": data.get("experience_narrative", ""),
            }
        elif detail_level == "narrative":
            return {
                "success": True,
                "session_id": session_id,
                "narrative": data.get("experience_narrative", ""),
            }
        else:
            return {"success": True, **data}

    def _cmd_eeg_list_sessions(self, params: dict) -> dict:
        limit = params.get("limit", 10)

        if not os.path.exists(SESSION_DIR):
            return {"success": True, "sessions": [], "count": 0}

        sessions = []
        files = sorted(
            [f for f in os.listdir(SESSION_DIR) if f.endswith(".json")],
            reverse=True,
        )

        for filename in files[:limit]:
            filepath = os.path.join(SESSION_DIR, filename)
            try:
                with open(filepath) as f:
                    data = json.load(f)
                sessions.append({
                    "session_id": data.get("session_id", filename.replace(".json", "")),
                    "track_title": data.get("track_title", "Unknown"),
                    "listener": data.get("listener", "Unknown"),
                    "duration_ms": data.get("duration_ms", 0),
                    "created_at": data.get("created_at", ""),
                    "chills_count": data.get("summary", {}).get("chills_count", 0),
                })
            except Exception as e:
                logger.warning(f"Failed to read {filename}: {e}")

        return {
            "success": True,
            "sessions": sessions,
            "count": len(sessions),
            "total_available": len(files),
        }

    def _cmd_eeg_calibrate_baseline(self, params: dict) -> dict:
        if not self.connection.board:
            return {"success": False, "error": "Not connected. Call eeg_connect first."}

        return {
            "success": True,
            "message": "Baseline calibration ready",
            "listener": params.get("listener_name", "Listener"),
            "status": "ready_to_start",
            "instructions": [
                "1. Sit comfortably and relax",
                "2. When prompted, keep eyes OPEN for 30 seconds",
                "3. Then keep eyes CLOSED for 30 seconds",
                "4. Baseline will be saved for future sessions",
                "5. Run eeg_stream_start with session_name='calibration' to begin",
            ],
        }

    def _cmd_eeg_status(self, params: dict) -> dict:
        status = self.connection.get_status() if self.connection.board else {}
        return {
            "connected": self.connection.board is not None,
            "streaming": self.connection.is_streaming,
            "board_info": status,
            "active_session": self.current_session["id"] if self.current_session else None,
            "moments_recorded": len(self.session_moments),
        }

    def get_telemetry_snapshot(self) -> Optional[dict]:
        """Get current emotion data for telemetry push (non-blocking)."""
        if not self.connection.is_streaming:
            return None

        try:
            conn = self.connection
            data = conn.get_current_data(conn.sampling_rate)
            if data is None or data.shape[1] < conn.sampling_rate // 4:
                return None

            processed = self.processor.process_window(
                data, conn.eeg_channels, conn.channel_names
            )
            moment = self.mapper.process_moment(
                processed["band_powers"],
                timestamp_ms=0,
                track_position="live",
                include_raw=False,
            )

            return {
                "valence": round(moment.valence, 3),
                "arousal": round(moment.arousal, 3),
                "attention": round(moment.attention, 3),
                "engagement": round(moment.engagement, 3),
                "possible_chills": moment.possible_chills,
            }
        except Exception:
            return None

    @staticmethod
    def _format_timestamp(ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def _interpret_emotion(valence: float, arousal: float) -> str:
        if valence > 0.4 and arousal > 0.6:
            return "Joyful/Excited"
        elif valence > 0.4 and arousal > 0.3:
            return "Happy/Content"
        elif valence > 0.4:
            return "Calm/Peaceful"
        elif valence < -0.2 and arousal > 0.6:
            return "Tense/Agitated"
        elif valence < -0.2:
            return "Sad/Melancholic"
        elif arousal > 0.6:
            return "Alert/Engaged"
        else:
            return "Neutral/Relaxed"


# ─── Bridge Client ──────────────────────────────────────────────────

class EEGBridgeClient:
    """
    WebSocket bridge client connecting local EEG hardware to ApexAurum Cloud.

    Mirrors the SensorHead bridge pattern:
    - Connect outward to Cloud WebSocket
    - Receive commands, execute locally, send responses
    - Push telemetry (emotion data) periodically
    - Auto-reconnect on disconnect
    """

    def __init__(self, token: str, url: str = DEFAULT_URL):
        self.token = token
        self.url = url
        self.eeg = EEGManager()
        self._running = True
        self._ws: Optional[websockets.WebSocketClientProtocol] = None

    async def run(self):
        """Main loop: connect, handle messages, reconnect on failure."""
        print()
        print(f"{GOLD}{BOLD}{'=' * 56}{RESET}")
        print(f"{GOLD}{BOLD}  EEG Bridge Client — ApexAurum Cloud{RESET}")
        print(f"{GOLD}{BOLD}  OpenBCI → Cloud WebSocket Tunnel{RESET}")
        print(f"{GOLD}{BOLD}{'=' * 56}{RESET}")
        print()
        info(f"Cloud: {self.url}")
        info(f"Token: {self.token[:16]}...")
        print()

        while self._running:
            try:
                await self._connect_and_listen()
            except (
                websockets.exceptions.ConnectionClosedError,
                websockets.exceptions.ConnectionClosedOK,
                ConnectionRefusedError,
                OSError,
            ) as e:
                error(f"Connection lost: {e}")
            except Exception as e:
                error(f"Unexpected error: {e}")
                logger.exception("Bridge error")

            if self._running:
                info(f"Reconnecting in {RECONNECT_DELAY}s...")
                await asyncio.sleep(RECONNECT_DELAY)

    async def _connect_and_listen(self):
        """Connect to Cloud and handle messages."""
        ws_url = f"{self.url}?token={self.token}"

        info("Connecting to Cloud...")
        async with websockets.connect(
            ws_url,
            ping_interval=PING_INTERVAL,
            ping_timeout=PING_INTERVAL * 2,
            max_size=10 * 1024 * 1024,  # 10MB for large session data
        ) as ws:
            self._ws = ws
            success("Connected to ApexAurum Cloud!")

            # Start telemetry push task
            telemetry_task = asyncio.create_task(self._telemetry_loop(ws))

            try:
                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON from Cloud")
                        continue

                    msg_type = msg.get("type")

                    if msg_type == "command":
                        await self._handle_command(ws, msg)
                    elif msg_type == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                    else:
                        logger.debug(f"Unknown message type: {msg_type}")
            finally:
                telemetry_task.cancel()
                try:
                    await telemetry_task
                except asyncio.CancelledError:
                    pass
                self._ws = None

    async def _handle_command(
        self, ws: websockets.WebSocketClientProtocol, msg: dict
    ):
        """Handle a command from the Cloud."""
        cmd_id = msg.get("id", "")
        action = msg.get("action", "")
        params = msg.get("params", {})

        info(f"Command: {action} (id={cmd_id[:12]}...)")

        # Run command in thread pool to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, self.eeg.handle_command, action, params
        )

        # Send response
        response = {
            "type": "response",
            "id": cmd_id,
            **result,
        }

        await ws.send(json.dumps(response, default=str))

        status_icon = f"{GREEN}OK{RESET}" if result.get("success") else f"{RED}ERR{RESET}"
        duration = result.get("duration_ms", 0)
        logger.info(f"  -> [{status_icon}] {action} ({duration}ms)")

    async def _telemetry_loop(self, ws: websockets.WebSocketClientProtocol):
        """Periodically push emotion telemetry to Cloud."""
        while True:
            await asyncio.sleep(TELEMETRY_INTERVAL)

            snapshot = self.eeg.get_telemetry_snapshot()
            if snapshot:
                try:
                    telemetry_msg = {
                        "type": "telemetry",
                        "readings": snapshot,
                        "timestamp": time.time(),
                    }
                    await ws.send(json.dumps(telemetry_msg))
                except Exception:
                    pass  # Non-fatal, will retry

    def shutdown(self):
        """Graceful shutdown."""
        info("Shutting down...")
        self._running = False

        # Disconnect EEG if connected
        if self.eeg.connection.board:
            try:
                if self.eeg.connection.is_streaming:
                    self.eeg.connection.stop_stream()
                self.eeg.connection.disconnect()
                success("EEG disconnected")
            except Exception as e:
                logger.warning(f"Disconnect error: {e}")


# ─── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="EEG Bridge Client — Connect OpenBCI to ApexAurum Cloud",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using environment variables (recommended)
  export EEG_BRIDGE_TOKEN="apex_dev_your_token"
  python eeg_bridge.py

  # Using command line arguments
  python eeg_bridge.py --token apex_dev_xxx

  # Testing with synthetic board
  python eeg_bridge.py --token apex_dev_xxx

  # Custom cloud URL (e.g., local development)
  python eeg_bridge.py --token apex_dev_xxx --url ws://localhost:8000/ws/bridge
        """,
    )

    parser.add_argument(
        "--token",
        default=os.environ.get("EEG_BRIDGE_TOKEN"),
        help="Device token (apex_dev_...). Default: $EEG_BRIDGE_TOKEN",
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("EEG_BRIDGE_URL", DEFAULT_URL),
        help=f"Cloud WebSocket URL. Default: {DEFAULT_URL}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if not args.token:
        error("No device token provided!")
        print()
        print("  Set EEG_BRIDGE_TOKEN environment variable or use --token flag.")
        print("  Get a token from the ApexAurum dashboard: Devices > Add Device > EEG Headset")
        print()
        sys.exit(1)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    client = EEGBridgeClient(token=args.token, url=args.url)

    # Handle Ctrl+C gracefully
    loop = asyncio.new_event_loop()

    def handle_signal(sig, frame):
        client.shutdown()
        loop.call_soon_threadsafe(loop.stop)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        loop.run_until_complete(client.run())
    except KeyboardInterrupt:
        client.shutdown()
    finally:
        loop.close()
        print()
        success("EEG Bridge Client stopped.")


if __name__ == "__main__":
    main()
