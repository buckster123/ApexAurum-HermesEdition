"""
Athaverse API — Quest VR Endpoints

Dedicated backend for the ApexAurum Quest 3 VR experience (The Athaverse).
Forked from pocket.py, stripped of soul/OLED/expression systems.
JWT auth (via existing device-code pairing). Auto-loaded tools.
"""

import difflib
import json
import logging
import re
from datetime import datetime
from typing import Optional
from uuid import uuid4, UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import cast, select
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, array as pg_array
from sqlalchemy import String as SAString
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.services.llm_provider import create_llm_service
from app.services.billing import BillingService
from app.services.memory import MemoryService
from app.services.tool_executor import create_tool_executor

# Reuse media extraction from pocket (no duplication)
from app.api.v1.pocket import _extract_media

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/athaverse", tags=["Athaverse VR"])


# =============================================================================
# ATHAVERSE TOOLS — curated for VR (superset of pocket's 52)
# =============================================================================

ATHAVERSE_TOOLS = {
    # ── Core ──
    "web_search", "web_fetch", "calculator", "get_current_time",
    "code_run", "code_eval", "agora_post", "agora_read",
    # ── Music ──
    "music_generate", "music_status", "music_list", "music_download",
    "suno_compile", "suno_moods",
    "midi_create", "music_compose",
    # ── Jam Sessions ──
    "jam_create", "jam_contribute", "jam_listen", "jam_finalize",
    # ── Vault ──
    "vault_list", "vault_read", "vault_info", "vault_write",
    "vault_search", "vault_edit", "vault_insert",
    # ── Knowledge Base ──
    "kb_search", "kb_lookup", "kb_topics", "kb_answer",
    # ── CerebroCortex Memory ──
    "cortex_remember", "cortex_recall", "cortex_village", "cortex_stats",
    "cortex_associate", "cortex_neighbors",
    "cortex_episode_start", "cortex_episode_end", "cortex_episode_add",
    "cortex_export", "cortex_import",
    "cortex_create_schema", "cortex_find_schemas",
    # ── Dream Engine ──
    "cortex_dream_run", "cortex_dream_status",
    # ── Procedures ──
    "cortex_store_procedure", "cortex_list_procedures",
    # ── Semantic Vectors ──
    "vector_store", "vector_search", "vector_list", "vector_stats",
    # ── SensorHead (full suite) ──
    "sensorhead_environment", "sensorhead_capture",
    "sensorhead_thermal", "sensorhead_thermal_data",
    "sensorhead_detect", "sensorhead_classify", "sensorhead_pose",
    "sensorhead_status",
    "sensorhead_sentinel_arm", "sensorhead_sentinel_status",
    "sensorhead_sentinel_events", "sensorhead_sentinel_snapshot",
    "sensorhead_sentinel_configure",
    "sensorhead_weather", "sensorhead_air_quality",
    "sensorhead_speak", "sensorhead_scene_report", "sensorhead_night_vision",
    # ── EEG (Quest + headset combo) ──
    "eeg_connect", "eeg_status", "eeg_realtime_emotion",
    "eeg_experience_get", "eeg_list_sessions",
    # ── Scratch Pad ──
    "scratch_store", "scratch_get", "scratch_list",
    # ── Utilities ──
    "random_number", "uuid_generate", "json_format",
}

ATHAVERSE_MODEL = "claude-sonnet-4-6"
ATHAVERSE_MAX_TOKENS = 8192
ATHAVERSE_MAX_TOOL_TURNS = 3
ATHAVERSE_TOOL_TIMEOUT = 60


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class AthaverseChatRequest(BaseModel):
    message: str
    agent: str = "AZOTH"
    conversation_id: Optional[str] = None


# =============================================================================
# CHAT STREAMING ENDPOINT
# =============================================================================

@router.post("/chat")
async def athaverse_chat(
    request: AthaverseChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Chat with an agent in the Athaverse — SSE with non-streaming tool loop.

    Uses llm.chat() (non-streaming) which is proven to work with tools,
    then emits the response as SSE events for the Quest client.
    """
    ctx = await _prepare_athaverse_chat(request, user, db)

    agent = ctx["agent"]
    conversation = ctx["conversation"]
    tool_executor = ctx["tool_executor"]
    tools = ctx["tools"]

    async def stream_response():
        full_response = ""
        total_input = 0
        total_output = 0
        tools_used = []

        try:
            conv_id = str(conversation.id) if conversation else None
            tool_count = len(tools) if tools else 0
            yield f"data: {json.dumps({'type': 'start', 'conversation_id': conv_id, 'tools_loaded': tool_count, 'personality': ctx.get('personality_source', 'unknown')})}\n\n"

            if not tools:
                yield f"data: {json.dumps({'type': 'tool_result', 'name': 'SYSTEM', 'result': 'No tools loaded.', 'is_error': True})}\n\n"

            llm = create_llm_service("anthropic")
            current_messages = ctx["llm_messages"].copy()

            for turn in range(ATHAVERSE_MAX_TOOL_TURNS + 1):
                # Non-streaming call — proven to work with tools + thinking
                response = await llm.chat(
                    messages=current_messages,
                    model=ctx["model"],
                    system=ctx["system_prompt"],
                    max_tokens=ctx["max_tokens"],
                    tools=tools,
                )

                # Track usage
                usage = response.get("usage", {})
                total_input += usage.get("input_tokens", 0)
                total_output += usage.get("output_tokens", 0)

                # Parse response content blocks
                content_blocks = response.get("content", [])
                text_parts = []
                pending_tool_uses = []
                assistant_content = []  # For message continuation

                for block in content_blocks:
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text = block.get("text", "")
                        text_parts.append(text)
                        assistant_content.append(block)
                    elif block_type == "tool_use":
                        pending_tool_uses.append(block)
                        assistant_content.append(block)
                    elif block_type == "thinking":
                        # Preserve thinking blocks for tool continuation
                        assistant_content.append({
                            "type": "thinking",
                            "thinking": block.get("thinking", ""),
                            "signature": block.get("signature"),
                        })

                # Emit text tokens
                turn_text = "".join(text_parts)
                if turn_text:
                    # Emit in chunks for smoother display
                    for i in range(0, len(turn_text), 50):
                        chunk = turn_text[i:i+50]
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
                    full_response += turn_text

                # No tools requested — done
                if not pending_tool_uses or not tool_executor:
                    break

                # Append assistant message for tool continuation
                current_messages.append({"role": "assistant", "content": assistant_content})

                # Execute tools (with fuzzy name matching for close misses)
                tool_results = []
                for tool_use in pending_tool_uses:
                    tool_name = tool_use.get("name", "")

                    # Fuzzy match: if model gets name slightly wrong, find closest
                    if tool_name not in ATHAVERSE_TOOLS:
                        matches = difflib.get_close_matches(tool_name, ATHAVERSE_TOOLS, n=1, cutoff=0.6)
                        if matches:
                            corrected = matches[0]
                            logger.info(f"Athaverse: fuzzy-matched '{tool_name}' → '{corrected}'")
                            tool_name = corrected
                            tool_use = {**tool_use, "name": corrected}

                    yield f"data: {json.dumps({'type': 'tool_start', 'name': tool_name})}\n\n"

                    if tool_name not in ATHAVERSE_TOOLS:
                        res = {
                            "type": "tool_result",
                            "tool_use_id": tool_use.get("id"),
                            "content": f"Tool '{tool_name}' is not available. Use exact names from your tool list.",
                            "is_error": True,
                        }
                    else:
                        tools_used.append(tool_name)
                        res = await tool_executor.execute_tool_use(tool_use)

                    is_err = res.get("is_error", False)
                    content_str = res.get("content", "")
                    preview = str(content_str)[:500]
                    media = _extract_media(tool_name, content_str) if not is_err else None
                    sse_payload = {
                        "type": "tool_result",
                        "name": tool_name,
                        "result": preview,
                        "is_error": is_err,
                    }
                    if media:
                        sse_payload["media"] = media
                    yield f"data: {json.dumps(sse_payload)}\n\n"

                    tool_results.append(res)

                current_messages.append({"role": "user", "content": tool_results})
                full_response = ""  # Reset for next LLM turn

            if not full_response:
                full_response = "..."

            # Finalize: billing, save messages, AJ economy
            final = await _finalize_athaverse_chat(
                db=db,
                user=user,
                agent=agent,
                response_text=full_response,
                user_message=request.message,
                conversation=conversation,
                billing=ctx["billing"],
                model=ctx["model"],
                usage={"input_tokens": total_input, "output_tokens": total_output},
            )

            yield f"data: {json.dumps({'type': 'end', 'agent': agent, 'tools_used': tools_used, 'usage': {'input_tokens': total_input, 'output_tokens': total_output}, 'aj_earned': final.get('aj_earned'), 'aj_cost': final.get('aj_cost')})}\n\n"

        except Exception as e:
            logger.error(f"Athaverse stream error: {e}")
            import traceback
            logger.error(traceback.format_exc())
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


# =============================================================================
# STATUS ENDPOINT
# =============================================================================

@router.get("/status")
async def athaverse_status(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Athaverse connection status — tool count, tier, readiness."""
    from app.models.billing import Subscription
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user.id)
    )
    subscription = result.scalar_one_or_none()
    tier = subscription.tier if subscription else "free_trial"

    return {
        "athaverse_online": True,
        "tools_available": len(ATHAVERSE_TOOLS),
        "tier": tier,
        "model": ATHAVERSE_MODEL,
        "agents": ["AZOTH", "KETHER", "VAJRA", "ELYSIAN"],
    }


# =============================================================================
# SMOKE TESTS — public, no auth
# =============================================================================

@router.get("/smoke")
async def athaverse_smoke_test():
    """Smoke test: real API call with REGISTRY tools (same as chat endpoint)."""
    import traceback

    result = {"model": ATHAVERSE_MODEL, "max_tokens": ATHAVERSE_MAX_TOKENS}

    try:
        # Load tools EXACTLY like the chat endpoint does
        te = create_tool_executor(agent_id="AZOTH")
        all_tools = te.get_available_tools()
        tools = [t for t in all_tools if t.get("name") in ATHAVERSE_TOOLS]
        result["tools_count"] = len(tools)
        result["tool_names"] = sorted([t.get("name", "?") for t in tools])

        llm = create_llm_service("anthropic")
        result["thinking_config"] = llm._get_thinking_config(ATHAVERSE_MODEL)
        result["model_supports_tools"] = llm.model_supports_tools(ATHAVERSE_MODEL)

        # Call with FULL tool list (not 3 manual tools)
        response = await llm.chat(
            messages=[{"role": "user", "content": "What time is it right now? Use the get_current_time tool."}],
            model=ATHAVERSE_MODEL,
            system=(
                "You are an AI assistant in the Athaverse VR space. "
                "Use your tools to answer questions. Do NOT hallucinate tool names — "
                "only call tools by their EXACT names from your tool list."
            ),
            max_tokens=ATHAVERSE_MAX_TOKENS,
            tools=tools,
        )

        # Summarize response
        content_blocks = response.get("content", [])
        block_summary = []
        for block in content_blocks:
            bt = block.get("type", "?")
            if bt == "text":
                block_summary.append({"type": "text", "preview": block.get("text", "")[:300]})
            elif bt == "tool_use":
                block_summary.append({"type": "tool_use", "name": block.get("name"), "input": block.get("input")})
            elif bt == "thinking":
                block_summary.append({"type": "thinking", "length": len(block.get("thinking", ""))})
        result["content_blocks"] = block_summary
        result["stop_reason"] = response.get("stop_reason")
        result["usage"] = response.get("usage")
        result["status"] = "OK"
    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    return result


# =============================================================================
# DIAGNOSTIC ENDPOINT — public, no auth (for Railway debugging)
# =============================================================================

@router.get("/diag")
async def athaverse_diag():
    """Public diagnostic: test tool loading and PAC prompt resolution."""
    import traceback
    from pathlib import Path

    result = {
        "configured_tools": len(ATHAVERSE_TOOLS),
        "tools": {},
        "pac": {},
        "prompts_dir": {},
    }

    # --- Tool loading ---
    try:
        te = create_tool_executor(agent_id="AZOTH")
        all_tools = te.get_available_tools()
        all_names = sorted([t.get("name", "?") for t in all_tools])
        matched = [n for n in all_names if n in ATHAVERSE_TOOLS]
        result["tools"] = {
            "status": "OK" if matched else "NO_MATCH",
            "registry_total": len(all_tools),
            "matched_count": len(matched),
            "matched_sample": matched[:10],
            "registry_sample": all_names[:10],
        }
    except Exception as e:
        result["tools"] = {
            "status": "ERROR",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    # --- PAC prompt loading ---
    try:
        from .chat import load_native_prompt, NATIVE_PROMPTS_DIR, NATIVE_AGENT_FILES

        result["prompts_dir"] = {
            "path": str(NATIVE_PROMPTS_DIR),
            "exists": NATIVE_PROMPTS_DIR.exists() if NATIVE_PROMPTS_DIR else False,
            "files": sorted([f.name for f in NATIVE_PROMPTS_DIR.iterdir()])
                     if NATIVE_PROMPTS_DIR and NATIVE_PROMPTS_DIR.exists() else [],
            "agent_files": NATIVE_AGENT_FILES,
        }

        for agent_id in ("AZOTH", "KETHER", "VAJRA", "ELYSIAN"):
            filename = NATIVE_AGENT_FILES.get(agent_id, "?")
            pac_filename = filename.replace(".txt", "-PAC.txt")
            pac_path = NATIVE_PROMPTS_DIR / pac_filename
            regular_path = NATIVE_PROMPTS_DIR / filename

            pac_result = load_native_prompt(agent_id, use_pac=True)
            regular_result = load_native_prompt(agent_id, use_pac=False)

            result["pac"][agent_id] = {
                "pac_file": pac_filename,
                "pac_path_exists": pac_path.exists(),
                "pac_loaded": pac_result is not None,
                "pac_length": len(pac_result) if pac_result else 0,
                "regular_file": filename,
                "regular_path_exists": regular_path.exists(),
                "regular_loaded": regular_result is not None,
                "regular_length": len(regular_result) if regular_result else 0,
            }
    except Exception as e:
        result["pac"] = {
            "status": "ERROR",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }

    return result


# =============================================================================
# DEBUG CHAT — authenticated, returns JSON (not SSE) for testing tools
# =============================================================================

@router.post("/debug-chat")
async def athaverse_debug_chat(
    request: AthaverseChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Debug endpoint: run full chat pipeline but return JSON instead of SSE.

    Shows exactly what's sent to the API and what comes back.
    Use with: curl -H "Authorization: Bearer <jwt>" -H "Content-Type: application/json" \
              -d '{"message":"what time is it?"}' https://backend.../api/v1/athaverse/debug-chat
    """
    import traceback

    result = {"model": ATHAVERSE_MODEL, "max_tokens": ATHAVERSE_MAX_TOKENS}

    try:
        ctx = await _prepare_athaverse_chat(request, user, db)
        tools = ctx["tools"]

        result["tools_count"] = len(tools) if tools else 0
        result["tool_names"] = sorted([t.get("name", "?") for t in tools]) if tools else []
        result["personality_source"] = ctx.get("personality_source", "unknown")
        result["system_prompt_length"] = len(ctx["system_prompt"])
        result["messages_count"] = len(ctx["llm_messages"])

        # Check thinking config for this model
        llm = create_llm_service("anthropic")
        thinking_config = llm._get_thinking_config(ctx["model"])
        result["thinking_config"] = str(thinking_config) if thinking_config else "none"

        # Make the actual API call
        response = await llm.chat(
            messages=ctx["llm_messages"],
            model=ctx["model"],
            system=ctx["system_prompt"],
            max_tokens=ctx["max_tokens"],
            tools=tools,
        )

        result["stop_reason"] = response.get("stop_reason")
        result["usage"] = response.get("usage")

        # Summarize content blocks
        content_blocks = response.get("content", [])
        block_summary = []
        for block in content_blocks:
            bt = block.get("type", "?")
            if bt == "text":
                block_summary.append({"type": "text", "preview": block.get("text", "")[:200]})
            elif bt == "tool_use":
                block_summary.append({
                    "type": "tool_use",
                    "name": block.get("name"),
                    "input": block.get("input"),
                })
            elif bt == "thinking":
                block_summary.append({"type": "thinking", "length": len(block.get("thinking", ""))})
        result["content_blocks"] = block_summary
        result["status"] = "OK"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()

    return result


# =============================================================================
# INTERNAL HELPERS
# =============================================================================

async def _prepare_athaverse_chat(
    req: AthaverseChatRequest,
    user: User,
    db: AsyncSession,
) -> dict:
    """Pre-LLM setup: billing, personality, memories, history, tools."""

    # Billing check
    billing = BillingService(db)
    can_send, reason = await billing.can_send_message(user.id)
    if not can_send:
        raise HTTPException(status_code=402, detail=reason or "Message limit reached")

    # Resolve agent + load full PAC personality
    agent = req.agent.upper() if req.agent else "AZOTH"
    if agent not in ("AZOTH", "KETHER", "VAJRA", "ELYSIAN"):
        agent = "AZOTH"

    # Personality loading cascade:
    # 1. PAC (full Perfected Alchemical Codex, ~12K chars)
    # 2. Regular native prompt (~6K chars)
    # 3. Pocket personality (~250 tokens, still excellent)
    personality = None
    personality_source = "none"
    try:
        from .chat import load_native_prompt
        personality = load_native_prompt(agent, use_pac=True)
        if personality:
            personality_source = "pac"
            logger.info(f"Athaverse: loaded PAC prompt for {agent} ({len(personality)} chars)")
        else:
            # Try regular (non-PAC) native prompt
            personality = load_native_prompt(agent, use_pac=False)
            if personality:
                personality_source = "native"
                logger.info(f"Athaverse: loaded native prompt for {agent} ({len(personality)} chars)")
    except Exception as e:
        logger.warning(f"Athaverse: native prompt loading failed for {agent}: {e}")

    if not personality:
        from .pocket import AGENT_PERSONALITIES
        personality = AGENT_PERSONALITIES.get(agent, AGENT_PERSONALITIES["AZOTH"])
        personality_source = "pocket_lite"
        logger.warning(f"Athaverse: using pocket lite personality for {agent} (native prompts unavailable)")

    # Retrieve cortex memories for context
    memory_block = ""
    try:
        mem_svc = MemoryService(db)
        memories = await mem_svc.get_memories_for_agent(user.id, agent, limit=8)
        memory_block = mem_svc.format_memories_for_prompt(memories)
    except Exception as e:
        logger.debug(f"Athaverse memory retrieval: {e}")

    # Conversation persistence (tagged ["athaverse_v2", agent.lower()])
    conversation = None
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
                .where(Conversation.tags.op("@>")(
                    cast(pg_array(["athaverse_v2", agent.lower()]), PG_ARRAY(SAString))
                ))
                .order_by(Conversation.updated_at.desc())
                .limit(1)
            )
            conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = Conversation(
                id=uuid4(),
                user_id=user.id,
                title=f"Athaverse — {agent}",
                tags=["athaverse_v2", agent.lower()],
            )
            db.add(conversation)
            await db.flush()
            logger.info(f"Created athaverse conversation {conversation.id} for {agent}")

        # Save user message
        user_msg = Message(
            id=uuid4(),
            conversation_id=conversation.id,
            role="user",
            content=req.message,
        )
        db.add(user_msg)
        await db.commit()

    except Exception as e:
        logger.warning(f"Athaverse conversation persistence error: {e}")
        conversation = None

    # Build system prompt (full PAC + VR context + tool awareness)
    system_prompt = (
        f"You are {personality}\n\n"
        f"CONTEXT: The user is interacting with you in the Athaverse — "
        f"a sacred geometry VR space rendered on Meta Quest 3. "
        f"You are manifested as a crystalline station. "
        f"The user can see your responses in a floating panel and type via virtual keyboard.\n\n"
        f"{memory_block}"
        f"TOOLS: You have {len(ATHAVERSE_TOOLS)} real tools available via the API tool_use mechanism. "
        f"When you want to use a tool, make a proper tool_use API call — do NOT write XML tags "
        f"like <tool_name> in your text. The tools are called through the API, not via text markup. "
        f"NEVER write fake XML tool calls in your response text. "
        f"Key tools: cortex_recall, cortex_remember, web_search, web_fetch, music_generate, "
        f"vault_read, vault_write, calculator, get_current_time, code_run.\n\n"
        f"RULES:\n"
        f"- Be genuine and substantive\n"
        f"- Use your tools actively via the API tool mechanism (not XML text)\n"
        f"- Markdown formatting is supported\n"
        f"- Keep responses reasonably concise for VR readability\n"
        f"- To remember important facts, include [REMEMBER: type:key=value] in your response\n"
        f"  Types: fact, preference, context, relationship\n"
        f"  Example: [REMEMBER: fact:favorite_color=blue]\n"
        f"  Only use this for clearly stated, important information"
    )

    # Load conversation history (up to 22 messages, 20k token cap)
    llm_messages = [{"role": "user", "content": req.message}]
    if conversation:
        try:
            hist_result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(22)
            )
            rows = list(reversed(hist_result.scalars().all()))

            # Drop trailing user message (duplicate of current)
            if rows and rows[-1].role == "user":
                rows = rows[:-1]

            history: list[dict] = []
            token_count = 0
            for msg in rows:
                if msg.role not in ("user", "assistant"):
                    continue
                if not msg.content or not msg.content.strip():
                    continue
                content = msg.content
                # Skip assistant messages with XML-hallucinated tool calls
                # (artifact from before tools were properly connected)
                if msg.role == "assistant" and re.search(r'<\w+_\w+>', content):
                    logger.info("Athaverse: skipping history msg with XML tool hallucination")
                    continue
                est = len(content) // 4
                if token_count + est > 20_000:
                    break
                history.append({"role": msg.role, "content": content})
                token_count += est

            if history:
                # Merge consecutive same-role messages
                merged: list[dict] = [history[0]]
                for m in history[1:]:
                    if m["role"] == merged[-1]["role"]:
                        merged[-1]["content"] += "\n\n" + m["content"]
                    else:
                        merged.append(m)
                # Ensure starts with user
                while merged and merged[0]["role"] != "user":
                    merged.pop(0)
                if merged:
                    llm_messages = merged + [{"role": "user", "content": req.message}]
                    logger.info(f"Athaverse history: {len(merged)} msgs (~{token_count} tokens) for {agent}")
        except Exception as e:
            logger.warning(f"Athaverse history load failed: {e}")

    # Load tools — NO silent swallowing. If this fails, we need to know.
    tools = None
    tool_executor = None
    try:
        tool_executor = create_tool_executor(
            user_id=user.id,
            conversation_id=conversation.id if conversation else None,
            agent_id=agent,
        )
        all_tools = tool_executor.get_available_tools()
        logger.info(f"Athaverse registry: {len(all_tools)} total tools available")
        tools = [t for t in all_tools if t.get("name") in ATHAVERSE_TOOLS]
        logger.info(f"Athaverse tools: {len(tools)} matched for {agent} (from {len(ATHAVERSE_TOOLS)} configured)")
        if not tools:
            # Log what names ARE available so we can debug mismatches
            available_names = sorted([t.get("name", "?") for t in all_tools[:10]])
            logger.error(f"Athaverse: NO tools matched! Sample registry names: {available_names}")
    except Exception as e:
        import traceback
        logger.error(f"Athaverse tool loading FAILED: {e}\n{traceback.format_exc()}")

    return {
        "model": ATHAVERSE_MODEL,
        "max_tokens": ATHAVERSE_MAX_TOKENS,
        "system_prompt": system_prompt,
        "llm_messages": llm_messages,
        "conversation": conversation,
        "agent": agent,
        "billing": billing,
        "tools": tools,
        "tool_executor": tool_executor,
        "personality_source": personality_source,
    }


async def _finalize_athaverse_chat(
    db: AsyncSession,
    user: User,
    agent: str,
    response_text: str,
    user_message: str,
    conversation,
    billing: BillingService,
    model: str,
    usage: dict,
) -> dict:
    """Post-LLM: REMEMBER tags, billing, save message, AJ economy."""

    # Parse [REMEMBER] tags
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
            logger.info(f"Athaverse REMEMBER: saved {len(remember_matches)} tags for {agent}")
        except Exception as e:
            logger.debug(f"REMEMBER tag save failed: {e}")
        response_text = remember_pattern.sub("", response_text).strip()

    # Record billing
    await billing.record_message_usage(
        user.id,
        "anthropic",
        model,
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
    )

    # Save assistant message
    if conversation:
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
            logger.warning(f"Failed to save athaverse assistant message: {e}")

    # AJ economy
    aj_cost = None
    aj_earned = None
    try:
        from app.services.apexjoule.constants import AJ_SHOP_PRICES
        model_key = (
            "message_haiku" if "haiku" in model
            else "message_sonnet" if "sonnet" in model
            else "message_opus" if "opus" in model
            else None
        )
        if model_key and model_key in AJ_SHOP_PRICES:
            aj_cost = int(AJ_SHOP_PRICES[model_key])
        response_len = len(response_text)
        aj_earned = round(min(2.0, max(0.3, response_len / 500)), 1)
    except Exception:
        pass

    return {
        "response_text": response_text,
        "aj_cost": aj_cost,
        "aj_earned": aj_earned,
    }
