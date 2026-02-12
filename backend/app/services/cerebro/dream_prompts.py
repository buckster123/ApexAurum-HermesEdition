"""LLM prompts for the CerebroCortex Dream Engine.

Extracted from CerebroCore for use with the cloud async engine.
All prompts request structured JSON responses.
"""

SYSTEM_DREAM = (
    "You are the Dream Engine of CerebroCortex, a brain-analogous AI memory system. "
    "You process memories during consolidation, extracting patterns, creating schemas, "
    "and finding unexpected connections. Respond in structured JSON only."
)

PROMPT_EXTRACT_PATTERNS = """Analyze these memories and extract reusable patterns or procedures.

Memories:
{memories}

Return a JSON array of extracted patterns. Each pattern should have:
- "content": A clear, actionable procedure or pattern (1-3 sentences)
- "source_indices": Which memory indices (0-based) this pattern comes from
- "tags": Relevant tags for the pattern

Return ONLY valid JSON array. Example:
[{{"content": "When debugging async code, check the event loop first, then verify awaits", "source_indices": [0, 2], "tags": ["debugging", "async"]}}]"""

PROMPT_FORM_SCHEMA = """Analyze these related memories and form an abstract schema (general principle).

Memories:
{memories}

What general principle, pattern, or lesson connects these memories?

Return JSON with:
- "content": The abstract principle (1-2 sentences, general enough to apply beyond these specific cases)
- "tags": Relevant categorization tags

Return ONLY valid JSON object. Example:
{{"content": "Iterative refinement with user feedback produces better results than upfront design", "tags": ["methodology", "development"]}}"""

PROMPT_REM_CONNECT = """You are looking at two seemingly unrelated memories. Find an unexpected but meaningful connection.

Memory A: {memory_a}
Memory B: {memory_b}

Is there a meaningful connection between these? If yes, describe it.

Return JSON with:
- "connected": true/false
- "link_type": One of: semantic, causal, supports, contradicts
- "reason": Brief explanation of the connection (1 sentence)
- "weight": Connection strength 0.0-1.0

Return ONLY valid JSON object."""
