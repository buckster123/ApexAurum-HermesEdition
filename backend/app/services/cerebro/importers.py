"""Universal Memory Import — Format Parsers for CerebroCortex Cloud.

Pure parsing functions that detect format and extract memories from files.
No DB dependency — returns ParseResult for preview, then commit routes through
CerebroCortexService.remember() for full pipeline processing.

Supported formats:
  .md    — YAML frontmatter + ## sections / paragraphs
  .txt   — Double-newline paragraph splitting
  .json  — Flat array, CerebroCortex v2, NeoCortex v1, ChatGPT export, Claude export
  .csv   — 'content' column required; optional: type, tags, agent_id, salience
  .sqlite/.db — ChromaDB or legacy ApexAurum databases

"The Crucible accepts all raw materials — mercury, sulphur, or salt."
"""

import csv
import io
import json
import logging
import re
import sqlite3
import tempfile
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("cerebro-import")

MAX_SQLITE_SIZE = 50 * 1024 * 1024  # 50 MB


# =============================================================================
# Data structures
# =============================================================================

@dataclass
class ParsedMemory:
    """A single parsed memory ready for import."""
    content: str
    memory_type: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    agent_id: Optional[str] = None
    salience: Optional[float] = None
    visibility: str = "private"
    source_format: str = "unknown"
    source_index: int = 0


@dataclass
class ParseResult:
    """Result of parsing a file into memories."""
    format_detected: str
    memories: list[ParsedMemory] = field(default_factory=list)
    total_found: int = 0
    warnings: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


# =============================================================================
# Type mapping
# =============================================================================

VALID_MEMORY_TYPES = {"episodic", "semantic", "procedural", "affective", "prospective", "schematic"}

# Neo-Cortex message_type -> CerebroCortex memory_type
NEOCORTEX_TYPE_MAP = {
    "fact": "semantic",
    "observation": "semantic",
    "discovery": "semantic",
    "announcement": "semantic",
    "dialogue": "episodic",
    "question": "episodic",
    "reflection": "episodic",
    "task": "prospective",
    "reminder": "prospective",
    "protocol": "procedural",
    "workflow": "procedural",
    "rule": "schematic",
    "principle": "schematic",
    "emotion": "affective",
    "feedback": "affective",
    "greeting": "episodic",
    "bridge_message": "episodic",
}


# =============================================================================
# Main dispatcher
# =============================================================================

def detect_and_parse(filename: str, content: bytes) -> ParseResult:
    """Auto-detect format from extension + content inspection, then parse.

    Args:
        filename: Original filename (for extension detection).
        content: Raw file bytes.

    Returns:
        ParseResult with detected format and extracted memories.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # Decode text (try utf-8 first, then latin-1 fallback)
    text = None
    if ext not in ("sqlite", "db"):
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except UnicodeDecodeError:
                return ParseResult(
                    format_detected="unknown",
                    warnings=["Could not decode file as UTF-8 or Latin-1"],
                )

    # SQLite formats
    if ext in ("sqlite", "db") or (content[:16] == b"SQLite format 3\x00"):
        if len(content) > MAX_SQLITE_SIZE:
            return ParseResult(
                format_detected="sqlite_too_large",
                warnings=[f"SQLite file exceeds {MAX_SQLITE_SIZE // (1024*1024)}MB limit"],
            )
        return _parse_sqlite(content)

    # JSON
    if ext == "json" or (text and text.lstrip()[:1] in ("{", "[")):
        if text:
            return parse_json(text)

    # CSV
    if ext == "csv":
        if text:
            return parse_csv(text)

    # Markdown
    if ext in ("md", "markdown"):
        if text:
            return parse_markdown(text)

    # Plain text (default for .txt or unknown text)
    if text:
        return parse_plaintext(text)

    return ParseResult(
        format_detected="unknown",
        warnings=[f"Unsupported file format: .{ext}"],
    )


# =============================================================================
# JSON parser (6 sub-formats)
# =============================================================================

def parse_json(text: str) -> ParseResult:
    """Parse JSON content, auto-detecting sub-format."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return ParseResult(
            format_detected="json_invalid",
            warnings=[f"Invalid JSON: {e}"],
        )

    # Dict formats
    if isinstance(data, dict):
        # NeoCortex export: {collections: {...}}
        if "collections" in data:
            return _parse_json_neocortex(data)
        # CerebroCortex v2: {memories: [...], format_version: ...}
        if "memories" in data and isinstance(data["memories"], list):
            return _parse_json_cerebrocortex(data)
        # Dict with "records" key
        if "records" in data and isinstance(data["records"], list):
            return _parse_json_flat(data["records"])
        # Single dict — wrap in list
        if "content" in data:
            return _parse_json_flat([data])

        return ParseResult(
            format_detected="json_unknown",
            warnings=["JSON object has no recognized structure (expected 'collections', 'memories', 'records', or 'content' key)"],
        )

    # Array formats
    if isinstance(data, list) and len(data) > 0:
        first = data[0] if isinstance(data[0], dict) else {}

        # ChatGPT export: [{title, mapping: {id: {message: ...}}}]
        if "mapping" in first and "title" in first:
            return _parse_json_chatgpt(data)

        # Claude export: [{title, chat_messages: [...]}] or similar
        if "chat_messages" in first or ("uuid" in first and "name" in first):
            return _parse_json_claude(data)

        # Flat array of memory dicts
        if "content" in first or "text" in first:
            return _parse_json_flat(data)

        # Array of strings
        if isinstance(data[0], str):
            return _parse_json_string_array(data)

        return ParseResult(
            format_detected="json_unknown",
            warnings=["JSON array items have no recognized structure"],
        )

    return ParseResult(
        format_detected="json_empty",
        warnings=["JSON file is empty or has unrecognized root type"],
    )


def _parse_json_flat(records: list) -> ParseResult:
    """Parse flat array of memory dicts: [{content, type?, tags?, ...}]."""
    result = ParseResult(format_detected="json_flat")
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            result.warnings.append(f"Item {i}: not a dict, skipped")
            continue

        content = (rec.get("content") or rec.get("text") or "").strip()
        if not content or len(content) < 3:
            continue

        mem_type = rec.get("type") or rec.get("memory_type")
        if mem_type and mem_type not in VALID_MEMORY_TYPES:
            mem_type = None

        tags = rec.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        result.memories.append(ParsedMemory(
            content=content,
            memory_type=mem_type,
            tags=tags,
            agent_id=rec.get("agent_id"),
            salience=_safe_float(rec.get("salience")),
            visibility=rec.get("visibility", "private"),
            source_format="json_flat",
            source_index=i,
        ))

    result.total_found = len(result.memories)
    return result


def _parse_json_cerebrocortex(data: dict) -> ParseResult:
    """Parse CerebroCortex v2 export: {memories: [...], format_version, ...}."""
    result = ParseResult(
        format_detected="json_cerebrocortex",
        metadata={"format_version": data.get("format_version", "unknown")},
    )
    records = data.get("memories", [])

    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue

        content = (rec.get("content") or "").strip()
        if not content or len(content) < 3:
            continue

        meta = rec.get("metadata", {}) if isinstance(rec.get("metadata"), dict) else {}
        mem_type = meta.get("memory_type") or rec.get("memory_type")
        if mem_type and mem_type not in VALID_MEMORY_TYPES:
            mem_type = None

        tags = meta.get("tags", rec.get("tags", []))
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        result.memories.append(ParsedMemory(
            content=content,
            memory_type=mem_type,
            tags=tags,
            agent_id=meta.get("agent_id", rec.get("agent_id")),
            salience=_safe_float(meta.get("salience", rec.get("salience"))),
            visibility=meta.get("visibility", "private"),
            source_format="json_cerebrocortex",
            source_index=i,
        ))

    result.total_found = len(result.memories)
    return result


def _parse_json_neocortex(data: dict) -> ParseResult:
    """Parse Neo-Cortex export: {collections: {name: [records]}}."""
    result = ParseResult(
        format_detected="json_neocortex",
        metadata={
            "format_version": data.get("format_version", "1.0"),
            "agent_id": data.get("agent_id"),
        },
    )
    collections = data.get("collections", {})
    idx = 0

    for coll_name, records in collections.items():
        if not isinstance(records, list):
            continue
        for rec in records:
            if not isinstance(rec, dict):
                continue

            content = (rec.get("content") or "").strip()
            if not content or len(content) < 3:
                continue

            # Skip agent_profile records
            msg_type = rec.get("message_type", "")
            if msg_type == "agent_profile":
                continue

            mem_type = NEOCORTEX_TYPE_MAP.get(msg_type, "semantic")

            tags = rec.get("tags", [])
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags = [t.strip() for t in tags.split(",") if t.strip()]
            # Add provenance tag
            if msg_type:
                tags = [f"neo:{msg_type}"] + tags

            result.memories.append(ParsedMemory(
                content=content,
                memory_type=mem_type,
                tags=tags,
                agent_id=rec.get("agent_id", data.get("agent_id")),
                salience=_safe_float(rec.get("attention_weight")),
                visibility="shared" if "shared" in coll_name else "private",
                source_format="json_neocortex",
                source_index=idx,
            ))
            idx += 1

    result.total_found = len(result.memories)
    return result


def _parse_json_chatgpt(data: list) -> ParseResult:
    """Parse ChatGPT conversations.json export."""
    result = ParseResult(format_detected="json_chatgpt")
    idx = 0

    for conv in data:
        if not isinstance(conv, dict):
            continue
        title = conv.get("title", "Untitled")
        mapping = conv.get("mapping", {})
        if not isinstance(mapping, dict):
            continue

        # Extract user messages from mapping tree
        for node_id, node in mapping.items():
            if not isinstance(node, dict):
                continue
            message = node.get("message")
            if not isinstance(message, dict):
                continue
            if message.get("author", {}).get("role") != "user":
                continue

            content_parts = message.get("content", {}).get("parts", [])
            content = " ".join(str(p) for p in content_parts if isinstance(p, str)).strip()
            if not content or len(content) < 3:
                continue

            result.memories.append(ParsedMemory(
                content=content,
                memory_type="episodic",
                tags=["chatgpt-import", _slugify(title)],
                source_format="json_chatgpt",
                source_index=idx,
            ))
            idx += 1

    result.total_found = len(result.memories)
    if result.memories:
        result.metadata["conversations_found"] = len(data)
    return result


def _parse_json_claude(data: list) -> ParseResult:
    """Parse Claude conversation export."""
    result = ParseResult(format_detected="json_claude")
    idx = 0

    for conv in data:
        if not isinstance(conv, dict):
            continue
        title = conv.get("name") or conv.get("title") or "Untitled"

        messages = conv.get("chat_messages", [])
        if not isinstance(messages, list):
            continue

        for msg in messages:
            if not isinstance(msg, dict):
                continue
            if msg.get("sender") not in ("human", "user"):
                continue

            content = ""
            text_field = msg.get("text") or msg.get("content")
            if isinstance(text_field, str):
                content = text_field.strip()
            elif isinstance(text_field, list):
                parts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in text_field]
                content = " ".join(parts).strip()

            if not content or len(content) < 3:
                continue

            result.memories.append(ParsedMemory(
                content=content,
                memory_type="episodic",
                tags=["claude-import", _slugify(title)],
                source_format="json_claude",
                source_index=idx,
            ))
            idx += 1

    result.total_found = len(result.memories)
    if result.memories:
        result.metadata["conversations_found"] = len(data)
    return result


def _parse_json_string_array(data: list) -> ParseResult:
    """Parse simple array of strings."""
    result = ParseResult(format_detected="json_string_array")
    for i, item in enumerate(data):
        content = str(item).strip()
        if not content or len(content) < 3:
            continue
        result.memories.append(ParsedMemory(
            content=content,
            memory_type="semantic",
            source_format="json_string_array",
            source_index=i,
        ))
    result.total_found = len(result.memories)
    return result


# =============================================================================
# Markdown parser
# =============================================================================

def parse_markdown(text: str) -> ParseResult:
    """Parse markdown: YAML frontmatter + ## sections or paragraphs."""
    result = ParseResult(format_detected="markdown")

    defaults, body = _parse_frontmatter(text)
    sections = _extract_sections(body)

    default_type = defaults.get("type", "semantic")
    if default_type not in VALID_MEMORY_TYPES:
        default_type = "semantic"

    default_tags = defaults.get("tags", [])
    if isinstance(default_tags, str):
        default_tags = [t.strip() for t in default_tags.split(",") if t.strip()]

    default_agent = defaults.get("agent_id")

    for i, (title, content) in enumerate(sections):
        content = content.strip()
        if not content or len(content) < 3:
            continue

        full_content = f"{title}: {content}" if title else content

        tags = list(default_tags)
        if title:
            tag = _slugify(title)
            if tag and tag not in tags:
                tags.append(tag)

        result.memories.append(ParsedMemory(
            content=full_content,
            memory_type=default_type,
            tags=tags,
            agent_id=default_agent,
            salience=_safe_float(defaults.get("salience")),
            source_format="markdown",
            source_index=i,
        ))

    result.total_found = len(result.memories)
    if defaults:
        result.metadata["frontmatter"] = defaults
    return result


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter delimited by --- lines."""
    text = text.lstrip()
    if not text.startswith("---"):
        return {}, text

    lines = text.split("\n")
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}, text

    frontmatter = {}
    for line in lines[1:end_idx]:
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, val = line.split(":", 1)
        key = key.strip()
        val = val.strip()

        if val.startswith("[") and val.endswith("]"):
            items = val[1:-1].split(",")
            frontmatter[key] = [item.strip().strip("'\"") for item in items if item.strip()]
        elif val.lower() in ("true", "false"):
            frontmatter[key] = val.lower() == "true"
        else:
            frontmatter[key] = val.strip("'\"")

    body = "\n".join(lines[end_idx + 1:])
    return frontmatter, body


def _extract_sections(text: str) -> list[tuple[str, str]]:
    """Extract sections from markdown (## headings or paragraphs)."""
    heading_pattern = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    headings = list(heading_pattern.finditer(text))

    if headings:
        sections = []
        for i, match in enumerate(headings):
            title = match.group(1).strip()
            start = match.end()
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            body = text[start:end].strip()
            sections.append((title, body))
        return sections

    paragraphs = re.split(r"\n\s*\n", text)
    return [("", p.strip()) for p in paragraphs if p.strip()]


# =============================================================================
# Plain text parser
# =============================================================================

def parse_plaintext(text: str) -> ParseResult:
    """Parse plain text: double-newline paragraph splitting."""
    result = ParseResult(format_detected="plaintext")

    paragraphs = re.split(r"\n\s*\n", text.strip())
    for i, para in enumerate(paragraphs):
        content = para.strip()
        if not content or len(content) < 3:
            continue
        result.memories.append(ParsedMemory(
            content=content,
            memory_type="semantic",
            source_format="plaintext",
            source_index=i,
        ))

    result.total_found = len(result.memories)
    return result


# =============================================================================
# CSV parser
# =============================================================================

def parse_csv(text: str) -> ParseResult:
    """Parse CSV with 'content' column required; optional: type, tags, agent_id, salience."""
    result = ParseResult(format_detected="csv")

    try:
        reader = csv.DictReader(io.StringIO(text))
        fieldnames = reader.fieldnames or []

        if "content" not in fieldnames and "text" not in fieldnames:
            result.warnings.append(
                f"CSV must have a 'content' or 'text' column. Found: {', '.join(fieldnames)}"
            )
            return result

        content_key = "content" if "content" in fieldnames else "text"

        for i, row in enumerate(reader):
            content = (row.get(content_key) or "").strip()
            if not content or len(content) < 3:
                continue

            mem_type = row.get("type") or row.get("memory_type")
            if mem_type and mem_type not in VALID_MEMORY_TYPES:
                mem_type = None

            tags_raw = row.get("tags", "")
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

            result.memories.append(ParsedMemory(
                content=content,
                memory_type=mem_type,
                tags=tags,
                agent_id=row.get("agent_id"),
                salience=_safe_float(row.get("salience")),
                source_format="csv",
                source_index=i,
            ))

    except csv.Error as e:
        result.warnings.append(f"CSV parsing error: {e}")

    result.total_found = len(result.memories)
    return result


# =============================================================================
# SQLite parsers (ChromaDB + Legacy)
# =============================================================================

def _parse_sqlite(content: bytes) -> ParseResult:
    """Detect SQLite sub-type and parse."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as tmp:
            tmp.write(content)
            tmp.flush()

            conn = sqlite3.connect(tmp.name)
            conn.row_factory = sqlite3.Row

            # Detect type by inspecting tables
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}

            if "embedding_queue" in tables or "collections" in tables:
                result = _parse_chromadb(conn, tables)
            elif "cortex_shared" in tables or "cortex_private" in tables:
                result = _parse_legacy_sqlite(conn, tables)
            else:
                result = ParseResult(
                    format_detected="sqlite_unknown",
                    warnings=[f"SQLite tables not recognized: {', '.join(sorted(tables))}"],
                )

            conn.close()
            return result

    except sqlite3.DatabaseError as e:
        return ParseResult(
            format_detected="sqlite_corrupt",
            warnings=[f"SQLite database error: {e}"],
        )


def _parse_chromadb(conn: sqlite3.Connection, tables: set) -> ParseResult:
    """Parse ChromaDB SQLite database."""
    result = ParseResult(format_detected="chromadb_sqlite")
    idx = 0

    # ChromaDB stores documents in embedding_queue or embeddings_queue
    doc_table = "embedding_queue" if "embedding_queue" in tables else None
    if not doc_table and "embeddings_queue" in tables:
        doc_table = "embeddings_queue"

    # Also check embeddings table directly
    if not doc_table and "embeddings" in tables:
        doc_table = "embeddings"

    if doc_table:
        try:
            rows = conn.execute(f"SELECT * FROM {doc_table}").fetchall()
            columns = [desc[0] for desc in conn.execute(f"SELECT * FROM {doc_table} LIMIT 0").description]

            for row in rows:
                row_dict = dict(zip(columns, row))
                content = row_dict.get("document", row_dict.get("content", ""))
                if not content or not isinstance(content, str) or len(content.strip()) < 3:
                    continue

                # Parse metadata if available
                meta_raw = row_dict.get("metadata")
                meta = {}
                if meta_raw:
                    try:
                        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else {}
                    except (json.JSONDecodeError, TypeError):
                        pass

                tags = []
                if meta.get("tags"):
                    tags = meta["tags"] if isinstance(meta["tags"], list) else [meta["tags"]]

                result.memories.append(ParsedMemory(
                    content=content.strip(),
                    memory_type=meta.get("memory_type", "semantic"),
                    tags=tags,
                    agent_id=meta.get("agent_id"),
                    source_format="chromadb_sqlite",
                    source_index=idx,
                ))
                idx += 1

        except sqlite3.Error as e:
            result.warnings.append(f"Error reading {doc_table}: {e}")

    # Try segments/embeddings tables (newer ChromaDB format)
    if not result.memories and "segments" in tables:
        result.warnings.append("Newer ChromaDB format detected; segment-based parsing not yet supported")

    result.total_found = len(result.memories)
    if not result.memories:
        result.warnings.append("No documents found in ChromaDB database")
    return result


def _parse_legacy_sqlite(conn: sqlite3.Connection, tables: set) -> ParseResult:
    """Parse legacy ApexAurum SQLite database (cortex_shared/cortex_private)."""
    result = ParseResult(format_detected="legacy_sqlite")
    idx = 0

    for table in ("cortex_shared", "cortex_private"):
        if table not in tables:
            continue

        visibility = "shared" if "shared" in table else "private"

        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            columns = [desc[0] for desc in conn.execute(f"SELECT * FROM {table} LIMIT 0").description]

            for row in rows:
                row_dict = dict(zip(columns, row))
                content = row_dict.get("content", "")
                if not content or not isinstance(content, str) or len(content.strip()) < 3:
                    continue

                # Parse metadata JSON
                meta_raw = row_dict.get("metadata", "{}")
                meta = {}
                if meta_raw:
                    try:
                        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else {}
                    except (json.JSONDecodeError, TypeError):
                        pass

                msg_type = row_dict.get("message_type", meta.get("message_type", ""))
                mem_type = NEOCORTEX_TYPE_MAP.get(msg_type, "semantic")

                tags = meta.get("tags", [])
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except (json.JSONDecodeError, TypeError):
                        tags = [t.strip() for t in tags.split(",") if t.strip()]
                if msg_type:
                    tags = [f"legacy:{msg_type}"] + list(tags)

                result.memories.append(ParsedMemory(
                    content=content.strip(),
                    memory_type=mem_type,
                    tags=tags,
                    agent_id=row_dict.get("agent_id", meta.get("agent_id")),
                    salience=_safe_float(row_dict.get("attention_weight", meta.get("attention_weight"))),
                    visibility=visibility,
                    source_format="legacy_sqlite",
                    source_index=idx,
                ))
                idx += 1

        except sqlite3.Error as e:
            result.warnings.append(f"Error reading {table}: {e}")

    result.total_found = len(result.memories)
    if not result.memories:
        result.warnings.append("No memories found in legacy database")
    return result


# =============================================================================
# Helpers
# =============================================================================

def _safe_float(val) -> Optional[float]:
    """Safely convert to float, return None on failure."""
    if val is None:
        return None
    try:
        f = float(val)
        return f if 0.0 <= f <= 1.0 else None
    except (ValueError, TypeError):
        return None


def _slugify(text: str) -> str:
    """Convert text to a URL-safe slug for tags."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] if slug else ""
