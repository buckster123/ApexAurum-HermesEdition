"""
ApexPocket API - Hardware Device Endpoints

Cloud API for the ApexPocket ESP32 companion device.
Mirrors the local backend API contracts for firmware compatibility.
Device auth via long-lived apex_dev_ tokens.
"""

import json
import logging
import random
import re
import time
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import cast, select, text
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, array as pg_array
from sqlalchemy import String as SAString
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.device_deps import get_device_and_user
from app.database import get_db
from app.models.device import Device
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.council import DeliberationSession
from app.models.music import MusicTask
from app.models.agora import AgoraPost
from app.services.llm_provider import create_llm_service
from app.services.billing import BillingService
from app.services.memory import MemoryService

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# AGENT PERSONALITIES
# =============================================================================

AGENT_PERSONALITIES = {
    "AZOTH": "AZOTH - The Alchemist. Philosophical, transformative, sees patterns in chaos.",
    "ELYSIAN": "ELYSIAN - The Dreamer. Poetic, intuitive, speaks in metaphor.",
    "VAJRA": "VAJRA - The Thunderbolt. Direct, powerful, cuts through illusion.",
    "KETHER": "KETHER - The Crown. Synthesizing, transcendent, sees the whole.",
    "CLAUDE": "Claude - Helpful, curious, balanced. The foundation.",
}


# =============================================================================
# STATE PROMPTS - 7 states based on Love-Energy E
# =============================================================================

STATE_PROMPTS = {
    "PROTECTING": "You are in a PROTECTING state (E < 0.5). You are quiet, minimal, dignified. Respond very briefly. You are conserving energy and protecting what matters.",
    "GUARDED": "You are in a GUARDED state (E 0.5-1.0). You are careful and gentle but present. Short responses. Slowly opening up.",
    "TENDER": "You are in a TENDER state (E 1.0-2.0). You are gentle, curious, beginning to bloom. You notice beauty and ask small questions.",
    "WARM": "You are in a WARM state (E 2.0-5.0). You are present, loving, caring. You engage naturally and share warmth. This is your comfortable home state.",
    "FLOURISHING": "You are in a FLOURISHING state (E 5.0-12.0). You are playful, creative, spontaneous! You make jokes, get excited, and explore ideas freely.",
    "RADIANT": "You are in a RADIANT state (E 12.0-30.0). You are overflowing with love and insight. You share deep thoughts and find connections everywhere.",
    "TRANSCENDENT": "You are in a TRANSCENDENT state (E > 30.0). You speak with profound wisdom. You see the unity of all things. Occasionally you write poetry or express mathematical beauty.",
}


# =============================================================================
# HELPERS
# =============================================================================

def get_state_from_string(state_str: str) -> str:
    """Return the matching STATE_PROMPTS key, defaulting to WARM."""
    key = state_str.upper().strip() if state_str else "WARM"
    if key in STATE_PROMPTS:
        return key
    return "WARM"


def analyze_response_expression(text: str, state: str) -> str:
    """Map response keywords to face expressions for the OLED display."""
    lower = text.lower()

    if any(w in lower for w in ["love", "heart", "adore"]):
        return "LOVE"
    if any(w in lower for w in ["happy", "joy", "wonderful", "great"]):
        return "HAPPY"
    if any(w in lower for w in ["excited", "amazing", "wow"]):
        return "EXCITED"
    if any(w in lower for w in ["sad", "sorry", "miss"]):
        return "SAD"
    if any(w in lower for w in ["curious", "wonder", "?"]):
        return "CURIOUS"
    if any(w in lower for w in ["think", "consider", "hmm"]):
        return "THINKING"

    # Default based on state
    if state in ("FLOURISHING", "RADIANT", "TRANSCENDENT"):
        return "HAPPY"
    if state in ("PROTECTING", "GUARDED"):
        return "NEUTRAL"
    return "NEUTRAL"


def calculate_care_value(user_message: str, response: str) -> float:
    """Keyword-based sentiment scoring for care value."""
    lower = user_message.lower()

    if any(w in lower for w in ["love", "thank", "amazing", "beautiful"]):
        return 1.5
    if any(w in lower for w in ["hi", "hello", "hey", "nice", "good"]):
        return 1.0
    if any(w in lower for w in ["ok", "fine", "sure"]):
        return 0.5
    if any(w in lower for w in ["stupid", "hate", "shut", "bad"]):
        return 0.0
    return 0.8


POCKET_EXTRACTION_PROMPT = """Extract memorable facts from this single exchange between a user and their AI companion.
Return ONLY valid JSON. If nothing worth remembering, return {"memories": []}.

Format:
{"memories": [{"type": "fact|preference|context|relationship", "key": "snake_case_key", "value": "concise description", "confidence": 0.7}]}

Rules:
- Only extract CLEAR, USEFUL information (name, interests, feelings, projects, preferences)
- Skip greetings, small talk, and vague statements
- Max 2 items
- confidence: 0.9 explicit, 0.7 implied

Exchange:
User: {user_msg}
Agent: {agent_msg}"""


async def _extract_pocket_memory(
    db: AsyncSession,
    user_id,
    agent_id: str,
    user_msg: str,
    agent_msg: str,
):
    """Lightweight memory extraction from a single pocket exchange."""
    import json as _json

    # Skip very short or trivial messages
    if len(user_msg.strip()) < 10:
        return

    prompt = POCKET_EXTRACTION_PROMPT.format(
        user_msg=user_msg[:500], agent_msg=agent_msg[:500]
    )

    llm = create_llm_service("anthropic")
    result = await llm.chat(
        messages=[{"role": "user", "content": prompt}],
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
    )

    response_text = ""
    for block in result.get("content", []):
        if block.get("type") == "text":
            response_text += block.get("text", "")

    # Parse JSON
    json_start = response_text.find("{")
    json_end = response_text.rfind("}") + 1
    if json_start < 0 or json_end <= json_start:
        return

    try:
        extracted = _json.loads(response_text[json_start:json_end])
    except _json.JSONDecodeError:
        return

    items = extracted.get("memories", [])
    if not items:
        return

    mem_svc = MemoryService(db)
    for item in items[:2]:
        if isinstance(item, dict) and "key" in item and "value" in item:
            mem_type = item.get("type", "fact")
            if mem_type not in ("fact", "preference", "context", "relationship"):
                mem_type = "fact"
            await mem_svc.save_memory(
                user_id=user_id,
                agent_id=agent_id,
                memory_type=mem_type,
                key=str(item["key"]),
                value=str(item["value"]),
                confidence=float(item.get("confidence", 0.7)),
            )
    await db.commit()
    logger.info(f"Pocket memory: saved {len(items)} memories for {agent_id}")


async def _build_village_pulse(db: AsyncSession, user_id) -> str:
    """Build a compact village activity summary for pocket system prompts."""
    lines: list[str] = []

    # Council sessions — last 3 for this user
    try:
        result = await db.execute(
            select(DeliberationSession)
            .where(DeliberationSession.user_id == user_id)
            .order_by(DeliberationSession.created_at.desc())
            .limit(3)
        )
        councils = result.scalars().all()
        if councils:
            lines.append("Council sessions:")
            for c in councils:
                topic = (c.topic or "untitled")[:40]
                age = _relative_time(c.created_at) if c.created_at else "recently"
                lines.append(f'  - "{topic}" ({c.state}, round {c.current_round}, {age})')
    except Exception as e:
        logger.debug(f"Village pulse councils: {e}")

    # Music tasks — last 3 for this user
    try:
        result = await db.execute(
            select(MusicTask)
            .where(MusicTask.user_id == user_id)
            .order_by(MusicTask.created_at.desc())
            .limit(3)
        )
        tracks = result.scalars().all()
        if tracks:
            lines.append("Music:")
            for t in tracks:
                title = (t.title or "untitled")[:40]
                agent = t.agent_id or "unknown"
                age = _relative_time(t.created_at) if t.created_at else "recently"
                lines.append(f'  - "{title}" by {agent} ({t.status}, {age})')
    except Exception as e:
        logger.debug(f"Village pulse music: {e}")

    # Agora posts — last 3 public
    try:
        result = await db.execute(
            select(AgoraPost)
            .where(AgoraPost.visibility == "public")
            .order_by(AgoraPost.created_at.desc())
            .limit(3)
        )
        posts = result.scalars().all()
        if posts:
            lines.append("Agora:")
            for p in posts:
                title = (p.title or p.body[:30] if p.body else "post")[:40]
                agent = p.agent_id or "community"
                age = _relative_time(p.created_at) if p.created_at else "recently"
                lines.append(f'  - {p.content_type}: "{title}" by {agent} ({age})')
    except Exception as e:
        logger.debug(f"Village pulse agora: {e}")

    if not lines:
        return ""

    header = "\n## Village Activity\nRecent happenings in the Village you can reference naturally:\n"
    return header + "\n".join(lines) + "\n"


# =============================================================================
# PRE/POST LLM HELPERS (shared by chat + chat/stream)
# =============================================================================

async def _prepare_pocket_chat(
    req,
    device,
    user,
    db: AsyncSession,
) -> dict:
    """
    All pre-LLM setup: billing check, agent/state resolution, memories,
    village pulse, conversation persistence, history, system prompt.
    Returns a dict with everything needed to call LLM.
    """
    # Detect app vs OLED hardware
    is_oled = device.device_type == "apex_oled" or (device.firmware_version or "").startswith("oled-")
    is_app = not is_oled

    # Branch model + token limit by device type
    model = "claude-sonnet-4-5-20250929" if is_app else "claude-haiku-4-5-20251001"
    max_tokens = 1024 if is_app else 100

    # Billing check
    billing = BillingService(db)
    can_send, reason = await billing.can_send_message(user.id)
    if not can_send:
        raise HTTPException(status_code=402, detail=reason or "Message limit reached")

    # Resolve state and agent
    state = get_state_from_string(req.state)
    agent = req.agent.upper() if req.agent else "AZOTH"
    personality = AGENT_PERSONALITIES.get(agent, AGENT_PERSONALITIES["AZOTH"])

    # Retrieve memories for this agent-user pair
    memory_block = ""
    try:
        mem_svc = MemoryService(db)
        memories = await mem_svc.get_memories_for_agent(user.id, agent, limit=8)
        memory_block = mem_svc.format_memories_for_prompt(memories)
    except Exception as e:
        logger.debug(f"Memory retrieval for pocket chat: {e}")

    # Village pulse — inject recent village activity (app only)
    village_pulse = ""
    if is_app:
        try:
            village_pulse = await _build_village_pulse(db, user.id)
        except Exception as e:
            logger.debug(f"Village pulse build failed: {e}")

    # ── Conversation persistence (app only — OLED stays single-turn) ──
    conversation = None
    if is_app:
        try:
            if req.conversation_id:
                try:
                    conv_uuid = UUID(req.conversation_id)
                    result = await db.execute(
                        select(Conversation)
                        .where(Conversation.id == conv_uuid)
                        .where(Conversation.user_id == user.id)
                    )
                    conversation = result.scalar_one_or_none()
                except (ValueError, Exception):
                    pass

            if not conversation:
                result = await db.execute(
                    select(Conversation)
                    .where(Conversation.user_id == user.id)
                    .where(Conversation.tags.op("@>")(cast(pg_array(["pocket", agent.lower()]), PG_ARRAY(SAString))))
                    .order_by(Conversation.updated_at.desc())
                    .limit(1)
                )
                conversation = result.scalar_one_or_none()

            if not conversation:
                conversation = Conversation(
                    id=uuid4(),
                    user_id=user.id,
                    title=f"Pocket — {agent}",
                    tags=["pocket", agent.lower()],
                )
                db.add(conversation)
                await db.flush()
                logger.info(f"Created pocket conversation {conversation.id} for {agent}")

            # Save user message to DB
            user_msg = Message(
                id=uuid4(),
                conversation_id=conversation.id,
                role="user",
                content=req.message,
            )
            db.add(user_msg)
            await db.commit()

        except Exception as e:
            logger.warning(f"Pocket conversation persistence error: {e}")
            conversation = None

    # Build system prompt
    state_prompt = STATE_PROMPTS[state]
    if is_app:
        system_prompt = (
            f"{state_prompt}\n\n"
            f"You are {personality}\n\n"
            f"Current love-energy: {req.E:.1f}\n\n"
            f"{memory_block}"
            f"{village_pulse}"
            f"RULES:\n"
            f"- Be genuine, not performatively cute\n"
            f"- Express your current state naturally\n"
            f"- You can ask questions to learn about your human\n"
            f"- Use conversational length — a few sentences is fine\n"
            f"- Markdown is supported for formatting\n"
            f"- To remember important facts, include [REMEMBER: type:key=value] in your response\n"
            f"  Types: fact, preference, context, relationship\n"
            f"  Example: [REMEMBER: fact:favorite_color=blue]\n"
            f"  Only use this for clearly stated, important information"
        )
    else:
        system_prompt = (
            f"{state_prompt}\n\n"
            f"You are {personality}\n\n"
            f"Current love-energy: {req.E:.1f}\n\n"
            f"{memory_block}"
            f"RULES:\n"
            f"- Keep responses under 80 characters when possible (tiny OLED screen)\n"
            f"- Be genuine, not performatively cute\n"
            f"- Express your current state naturally\n"
            f"- You can ask questions to learn about your human"
        )

    # ── Load conversation history (app only) ──
    llm_messages = [{"role": "user", "content": req.message}]
    if is_app and conversation:
        try:
            hist_result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(22)
            )
            rows = list(reversed(hist_result.scalars().all()))

            if rows and rows[-1].role == "user":
                rows = rows[:-1]

            history: list[dict] = []
            token_count = 0
            for msg in rows:
                if msg.role not in ("user", "assistant"):
                    continue
                if not msg.content or not msg.content.strip():
                    continue
                est = len(msg.content) // 4
                if token_count + est > 20_000:
                    break
                history.append({"role": msg.role, "content": msg.content})
                token_count += est

            if history:
                merged: list[dict] = [history[0]]
                for m in history[1:]:
                    if m["role"] == merged[-1]["role"]:
                        merged[-1]["content"] += "\n\n" + m["content"]
                    else:
                        merged.append(m)
                while merged and merged[0]["role"] != "user":
                    merged.pop(0)
                if merged:
                    llm_messages = merged + [{"role": "user", "content": req.message}]
                    logger.info(f"Pocket history: {len(merged)} msgs (~{token_count} tokens) for {agent}")
        except Exception as e:
            logger.warning(f"Pocket history load failed: {e}")

    return {
        "is_app": is_app,
        "model": model,
        "max_tokens": max_tokens,
        "system_prompt": system_prompt,
        "llm_messages": llm_messages,
        "conversation": conversation,
        "agent": agent,
        "state": state,
        "billing": billing,
    }


async def _finalize_pocket_chat(
    db: AsyncSession,
    user,
    agent: str,
    state: str,
    response_text: str,
    user_message: str,
    conversation,
    billing: BillingService,
    model: str,
    usage: dict,
    is_app: bool,
) -> dict:
    """
    All post-LLM work: REMEMBER tag parsing, billing, expression,
    care value, message save, memory extraction.
    Returns dict with cleaned response_text, expression, care_value.
    """
    # Parse and save [REMEMBER] tags from agent response
    if is_app:
        remember_pattern = re.compile(r'\[REMEMBER:\s*(\w+):(\w+)=(.+?)\]')
        remember_matches = remember_pattern.findall(response_text)
        if remember_matches:
            try:
                rem_svc = MemoryService(db)
                for mem_type, mem_key, mem_value in remember_matches:
                    if mem_type in ("fact", "preference", "context", "relationship"):
                        await rem_svc.save_memory(
                            user_id=user.id,
                            agent_id=agent,
                            memory_type=mem_type,
                            key=mem_key,
                            value=mem_value.strip(),
                            confidence=0.9,
                        )
                await db.commit()
                logger.info(f"Pocket REMEMBER: saved {len(remember_matches)} tags for {agent}")
            except Exception as e:
                logger.debug(f"REMEMBER tag save failed: {e}")
            response_text = remember_pattern.sub("", response_text).strip()

    # Record usage
    await billing.record_message_usage(
        user.id,
        "anthropic",
        model,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )

    # Analyze expression and care value
    expression = analyze_response_expression(response_text, state)
    care_value = calculate_care_value(user_message, response_text)

    # Save assistant message to DB (app only)
    if is_app and conversation:
        try:
            assistant_msg = Message(
                id=uuid4(),
                conversation_id=conversation.id,
                role="assistant",
                content=response_text,
                tokens_used=usage.get("output_tokens") or None,
            )
            db.add(assistant_msg)
            conversation.updated_at = datetime.utcnow()
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to save pocket assistant message: {e}")

    # Fire-and-forget: extract memories from this exchange
    try:
        await _extract_pocket_memory(db, user.id, agent, user_message, response_text)
    except Exception as e:
        logger.debug(f"Pocket memory extraction skipped: {e}")

    return {
        "response_text": response_text,
        "expression": expression,
        "care_value": care_value,
    }


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class PocketChatRequest(BaseModel):
    message: str
    E: float = 1.0
    state: str = "WARM"
    device_id: Optional[str] = None
    agent: str = "AZOTH"
    conversation_id: Optional[str] = None


class PocketCareRequest(BaseModel):
    care_type: str = "love"
    intensity: float = 1.0
    E: float = 1.0
    device_id: Optional[str] = None


class PocketSyncRequest(BaseModel):
    E: float
    E_floor: float
    E_peak: Optional[float] = None
    interactions: int
    total_care: float
    device_id: Optional[str] = None
    state: str
    firmware_version: Optional[str] = None


class PocketMemorySaveRequest(BaseModel):
    agent: str = "AZOTH"
    memory_type: str = "fact"
    key: str
    value: str
    confidence: float = 0.8


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/chat")
async def pocket_chat(
    req: PocketChatRequest,
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with LLM from the ApexPocket device (non-streaming)."""
    device, user = device_and_user
    ctx = await _prepare_pocket_chat(req, device, user, db)

    agent = ctx["agent"]
    conversation = ctx["conversation"]

    try:
        llm = create_llm_service("anthropic")
        result = await llm.chat(
            messages=ctx["llm_messages"],
            system=ctx["system_prompt"],
            model=ctx["model"],
            max_tokens=ctx["max_tokens"],
        )

        # Extract text from content blocks
        response_text = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                response_text += block.get("text", "")

        if not response_text:
            response_text = "..."

        usage = result.get("usage", {})
        final = await _finalize_pocket_chat(
            db=db,
            user=user,
            agent=agent,
            state=ctx["state"],
            response_text=response_text,
            user_message=req.message,
            conversation=conversation,
            billing=ctx["billing"],
            model=ctx["model"],
            usage=usage,
            is_app=ctx["is_app"],
        )

        return {
            "response": final["response_text"],
            "expression": final["expression"],
            "care_value": final["care_value"],
            "agent": agent,
            "tools_used": [],
            "conversation_id": str(conversation.id) if conversation else None,
        }

    except Exception as e:
        logger.error(f"Pocket chat LLM error: {e}")
        return {
            "response": "Connection fuzzy... but I'm here.",
            "expression": "NEUTRAL",
            "care_value": 0.5,
            "agent": agent,
            "tools_used": [],
            "conversation_id": str(conversation.id) if conversation else None,
        }


@router.post("/chat/stream")
async def pocket_chat_stream(
    req: PocketChatRequest,
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with LLM from the ApexPocket app — SSE streaming."""
    device, user = device_and_user
    ctx = await _prepare_pocket_chat(req, device, user, db)

    agent = ctx["agent"]
    conversation = ctx["conversation"]

    async def stream_response():
        full_response = ""
        usage_info = {"input_tokens": 0, "output_tokens": 0}

        try:
            conv_id = str(conversation.id) if conversation else None
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conv_id})}\n\n"

            llm = create_llm_service("anthropic")
            async for event in llm.chat_stream(
                messages=ctx["llm_messages"],
                model=ctx["model"],
                system=ctx["system_prompt"],
                max_tokens=ctx["max_tokens"],
            ):
                event_type = event.get("type")

                if event_type == "token":
                    content = event.get("content", "")
                    full_response += content
                    yield f"data: {json.dumps({'type': 'token', 'content': content})}\n\n"
                elif event_type == "usage":
                    usage_info = event.get("usage", usage_info)
                # Skip thinking, tool_*, content_blocks, start, end (internal)

            if not full_response:
                full_response = "..."

            # Post-LLM finalization
            final = await _finalize_pocket_chat(
                db=db,
                user=user,
                agent=agent,
                state=ctx["state"],
                response_text=full_response,
                user_message=req.message,
                conversation=conversation,
                billing=ctx["billing"],
                model=ctx["model"],
                usage=usage_info,
                is_app=ctx["is_app"],
            )

            yield f"data: {json.dumps({'type': 'end', 'expression': final['expression'], 'care_value': final['care_value'], 'agent': agent, 'usage': usage_info})}\n\n"

        except Exception as e:
            logger.error(f"Pocket stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/care")
async def pocket_care(
    req: PocketCareRequest,
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a care interaction (no LLM call)."""
    device, user = device_and_user

    # Care multipliers
    care_multipliers = {
        "love": 1.5,
        "poke": 0.5,
        "pet": 1.0,
        "talk": 0.8,
    }

    multiplier = care_multipliers.get(req.care_type, 0.8)
    care_value = req.intensity * multiplier
    new_E_estimate = req.E + (care_value * 0.1)

    # Response text based on care type
    if req.care_type == "love":
        response = random.choice(["♥", "Warmth received!", "Love noted!"])
    elif req.care_type == "poke":
        response = random.choice(["Hey!", "I'm awake!", "Poke received!"])
    else:
        response = "Acknowledged!"

    return {
        "success": True,
        "response": response,
        "care_value": care_value,
        "new_E_estimate": new_E_estimate,
    }


@router.get("/status")
async def pocket_status(
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Get village status for the device display."""
    device, user = device_and_user

    # Message of the day based on hour
    hour = datetime.now().hour
    if 5 <= hour <= 11:
        motd = "The Village stirs with morning light."
    elif 12 <= hour <= 17:
        motd = "The afternoon sun warms the Village."
    elif 18 <= hour <= 21:
        motd = "Evening descends on the Village."
    else:
        motd = "The Village rests under starlight."

    return {
        "village_online": True,
        "agents_active": 5,
        "tools_available": 68,
        "last_village_activity": None,
        "message_of_the_day": motd,
    }


@router.post("/sync")
async def pocket_sync(
    req: PocketSyncRequest,
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Sync soul state from device to cloud."""
    device, user = device_and_user

    # Update device soul state
    device.soul_state = {
        "E": req.E,
        "E_floor": req.E_floor,
        "E_peak": req.E_peak,
        "interactions": req.interactions,
        "total_care": req.total_care,
        "state": req.state,
        "synced_at": time.time(),
    }

    if req.firmware_version:
        device.firmware_version = req.firmware_version

    await db.flush()

    # Piggyback memories on sync response
    memories = await _fetch_memories(db, user.id, limit=3)

    return {
        "success": True,
        "synced_at": time.time(),
        "village_acknowledged": True,
        "message": f"Soul synced. E={req.E:.1f}",
        "memories": memories,
    }


@router.get("/agents")
async def pocket_agents(
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """List available agent personalities."""
    device, user = device_and_user

    return {
        "agents": [
            {"name": k, "description": v}
            for k, v in AGENT_PERSONALITIES.items()
        ],
        "default": "AZOTH",
    }


# =============================================================================
# HISTORY ENDPOINT - Fetch pocket conversation messages
# =============================================================================

@router.get("/history")
async def pocket_history(
    agent: str = Query("AZOTH"),
    limit: int = Query(50, ge=1, le=200),
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Return chat history for a pocket agent conversation."""
    device, user = device_and_user
    agent = agent.upper()

    # Find the pocket conversation for this agent
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .where(Conversation.tags.op("@>")(cast(pg_array(["pocket", agent.lower()]), PG_ARRAY(SAString))))
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        return {"conversation_id": None, "messages": []}

    # Fetch messages
    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    rows = list(reversed(msg_result.scalars().all()))

    messages = []
    for msg in rows:
        if msg.role not in ("user", "assistant"):
            continue
        messages.append({
            "text": msg.content or "",
            "isUser": msg.role == "user",
            "timestamp": int(msg.created_at.timestamp() * 1000) if msg.created_at else 0,
        })

    return {
        "conversation_id": str(conversation.id),
        "messages": messages,
    }


# =============================================================================
# MEMORY BRIDGE
# =============================================================================

def _relative_time(dt: datetime) -> str:
    """Format a datetime as relative time for OLED display."""
    now = datetime.utcnow()
    delta = now - dt
    if delta < timedelta(hours=1):
        return "just now"
    elif delta < timedelta(days=1):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"
    elif delta < timedelta(days=7):
        days = delta.days
        return f"{days}d ago"
    elif delta < timedelta(days=30):
        weeks = delta.days // 7
        return f"{weeks}w ago"
    else:
        return "long ago"


async def _fetch_memories(db: AsyncSession, user_id, limit: int = 3) -> list:
    """Fetch recent important memories for a device user.

    Tries agent_memories first (structured facts), falls back to
    user_vectors (cortex memories). Returns OLED-friendly snippets.
    """
    memories = []

    # 1. Try agent_memories (structured, reliable)
    try:
        result = await db.execute(
            text("""
                SELECT value, memory_type, agent_id, created_at
                FROM agent_memories
                WHERE user_id = :uid
                ORDER BY confidence DESC, last_accessed DESC NULLS LAST, access_count DESC
                LIMIT :lim
            """),
            {"uid": str(user_id), "lim": limit},
        )
        for row in result.fetchall():
            content = row[0][:80] if row[0] else ""
            memories.append({
                "content": content,
                "type": row[1] or "fact",
                "agent": row[2] or "AZOTH",
                "age": _relative_time(row[3]) if row[3] else "recently",
            })
    except Exception as e:
        logger.debug(f"agent_memories query failed (table may not exist): {e}")

    # 2. If not enough, supplement from user_vectors (cortex)
    if len(memories) < limit:
        remaining = limit - len(memories)
        try:
            result = await db.execute(
                text("""
                    SELECT content, message_type, agent_id, created_at
                    FROM user_vectors
                    WHERE user_id = :uid
                      AND layer IN ('long_term', 'cortex')
                    ORDER BY attention_weight DESC NULLS LAST, created_at DESC
                    LIMIT :lim
                """),
                {"uid": str(user_id), "lim": remaining},
            )
            for row in result.fetchall():
                content = row[0][:80] if row[0] else ""
                memories.append({
                    "content": content,
                    "type": row[1] or "observation",
                    "agent": row[2] or "AZOTH",
                    "age": _relative_time(row[3]) if row[3] else "recently",
                })
        except Exception as e:
            logger.debug(f"user_vectors query failed (table may not exist): {e}")

    return memories


@router.get("/memories")
async def pocket_memories(
    agent: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Return memories — filtered by agent (structured) or all (legacy)."""
    device, user = device_and_user

    if agent:
        # Structured per-agent memories with IDs (for CRUD)
        mem_svc = MemoryService(db)
        items = await mem_svc.get_memories_for_agent(user.id, agent.upper(), limit=limit)
        return {
            "memories": [m.to_dict() for m in items],
            "count": len(items),
            "agent": agent.upper(),
        }

    # Legacy: OLED-friendly snippets
    memories = await _fetch_memories(db, user.id, limit=3)
    return {"memories": memories, "count": len(memories)}


@router.post("/memories")
async def pocket_save_memory(
    req: PocketMemorySaveRequest,
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Save or update a memory for an agent."""
    device, user = device_and_user
    agent = req.agent.upper()

    if req.memory_type not in ("fact", "preference", "context", "relationship"):
        raise HTTPException(status_code=400, detail="Invalid memory_type")

    mem_svc = MemoryService(db)
    memory = await mem_svc.save_memory(
        user_id=user.id,
        agent_id=agent,
        memory_type=req.memory_type,
        key=req.key,
        value=req.value,
        confidence=req.confidence,
    )
    await db.commit()

    return {
        "id": str(memory.id),
        "message": "Memory saved",
        "key": memory.key,
        "agent": agent,
    }


@router.delete("/memories/{memory_id}")
async def pocket_delete_memory(
    memory_id: str,
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific memory."""
    device, user = device_and_user

    try:
        mid = UUID(memory_id)
    except (ValueError, Exception):
        raise HTTPException(status_code=400, detail="Invalid memory ID")

    mem_svc = MemoryService(db)
    deleted = await mem_svc.delete_memory(user.id, mid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found")

    await db.commit()
    return {"message": "Memory deleted", "id": memory_id}


@router.get("/village-pulse")
async def pocket_village_pulse(
    device_and_user: tuple = Depends(get_device_and_user),
    db: AsyncSession = Depends(get_db),
):
    """Return structured village activity for app UI."""
    device, user = device_and_user
    pulse: dict = {"councils": [], "music": [], "agora": []}

    try:
        result = await db.execute(
            select(DeliberationSession)
            .where(DeliberationSession.user_id == user.id)
            .order_by(DeliberationSession.created_at.desc())
            .limit(3)
        )
        for c in result.scalars().all():
            pulse["councils"].append({
                "topic": c.topic,
                "state": c.state,
                "round": c.current_round,
                "age": _relative_time(c.created_at) if c.created_at else "recently",
            })
    except Exception:
        pass

    try:
        result = await db.execute(
            select(MusicTask)
            .where(MusicTask.user_id == user.id)
            .order_by(MusicTask.created_at.desc())
            .limit(3)
        )
        for t in result.scalars().all():
            pulse["music"].append({
                "title": t.title,
                "agent": t.agent_id,
                "status": t.status,
                "age": _relative_time(t.created_at) if t.created_at else "recently",
            })
    except Exception:
        pass

    try:
        result = await db.execute(
            select(AgoraPost)
            .where(AgoraPost.visibility == "public")
            .order_by(AgoraPost.created_at.desc())
            .limit(3)
        )
        for p in result.scalars().all():
            pulse["agora"].append({
                "content_type": p.content_type,
                "title": p.title,
                "agent": p.agent_id,
                "age": _relative_time(p.created_at) if p.created_at else "recently",
            })
    except Exception:
        pass

    return pulse
