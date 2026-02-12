"""Bridge Inference Relay — Route LLM calls through SensorHead Bridge.

Implements the same interface as MultiProviderLLM.chat() so the
AsyncDreamEngine can use it as a drop-in replacement. LLM inference
runs on the user's local hardware (Ollama, LM Studio, vLLM) through
the existing Bridge WebSocket tunnel.

Zero cost to the platform. The user's GPU does the work.
"""

import logging
from uuid import UUID

logger = logging.getLogger(__name__)


class BridgeInferenceRelay:
    """Routes LLM calls through the Bridge tunnel to local hardware.

    Implements async chat() matching MultiProviderLLM interface.
    """

    def __init__(self, device_id: UUID, user_id: UUID):
        self._device_id = device_id
        self._user_id = user_id

    async def chat(
        self,
        messages: list[dict],
        model: str = None,
        system: str = None,
        max_tokens: int = 1024,
        **kwargs,
    ) -> dict:
        """Send LLM request through Bridge tunnel.

        Uses the existing BridgeConnectionManager.send_command() pattern.
        The SensorHead's bridge client handles routing to local Ollama/LM Studio.

        Returns: MultiProviderLLM-compatible response dict.
        """
        from app.services.bridge_manager import get_bridge_manager

        manager = get_bridge_manager()

        result = await manager.send_command(
            device_id=self._device_id,
            action="inference_request",
            params={
                "messages": messages,
                "model": model,
                "system": system,
                "max_tokens": max_tokens,
            },
            timeout=120.0,
        )

        # Normalize to MultiProviderLLM response format
        data = result.get("data", {})
        text = data.get("text", "")
        usage = data.get("usage", {})

        return {
            "content": [{"type": "text", "text": text}],
            "usage": {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            "provider": "bridge_relay",
            "model": model or "local",
        }
