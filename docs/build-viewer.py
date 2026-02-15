#!/usr/bin/env python3
"""
Build script for tutorial-viewer.html
Reads all markdown tutorials, converts to HTML, and generates
a single self-contained viewer file.
"""

import os
import re
import html
import json

TUTORIALS_DIR = os.path.join(os.path.dirname(__file__), "tutorials")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "tutorial-viewer.html")

# Category definitions with display order
CATEGORIES = [
    {
        "id": "quick-start",
        "title": "Quick Start",
        "icon": "&#9889;",  # lightning bolt
        "files": [
            "01-first-boot.md",
            "02-pair-your-phone.md",
            "03-meet-the-agents.md",
            "04-your-first-memory.md",
            "05-sensorhead-basics.md",
        ],
    },
    {
        "id": "setup",
        "title": "Setup",
        "icon": "&#9881;",  # gear
        "files": [
            "01-sensorhead-build.md",
            "02-software-install.md",
            "03-cloud-pairing.md",
            "04-mobile-app.md",
            "05-voice-setup.md",
        ],
    },
    {
        "id": "deep",
        "title": "Deep Guides",
        "icon": "&#9733;",  # star
        "files": [
            "01-sentinel.md",
            "02-bme688-air-quality.md",
            "03-thermal-imaging.md",
            "04-cerebrocortex.md",
            "05-council.md",
            "06-music.md",
            "07-agent-personalities.md",
        ],
    },
    {
        "id": "troubleshooting",
        "title": "Troubleshooting",
        "icon": "&#128295;",  # wrench
        "files": [
            "sensorhead-offline.md",
            "camera-issues.md",
            "bme688-issues.md",
            "app-connection.md",
            "voice-issues.md",
        ],
    },
]


def estimate_reading_time(text):
    """Estimate reading time in minutes based on word count."""
    words = len(text.split())
    minutes = max(1, round(words / 200))
    return minutes


def md_to_html(md_text):
    """
    Convert markdown to HTML. Handles:
    - Headings (h1-h6)
    - Paragraphs
    - Code blocks (fenced with ```)
    - Inline code
    - Tables
    - Blockquotes
    - Ordered and unordered lists
    - Bold, italic
    - Links
    - Horizontal rules
    - Nested lists (basic)
    - Task lists (checkboxes)
    """
    lines = md_text.split("\n")
    html_parts = []
    i = 0
    in_list = None  # 'ul' or 'ol'
    list_indent = 0

    def close_list():
        nonlocal in_list
        if in_list:
            html_parts.append(f"</{in_list}>")
            in_list = None

    def inline_format(text):
        """Apply inline formatting: bold, italic, code, links."""
        # Inline code (must come before bold/italic to avoid conflicts)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        # Bold + italic
        text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
        # Bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
        # Italic
        text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
        # Links
        text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        # Double dash to em dash
        text = text.replace(" -- ", " &mdash; ")
        return text

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Empty line
        if not stripped:
            close_list()
            i += 1
            continue

        # Fenced code block
        if stripped.startswith("```"):
            close_list()
            lang = stripped[3:].strip()
            lang_attr = f' data-lang="{html.escape(lang)}"' if lang else ""
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(html.escape(lines[i]))
                i += 1
            i += 1  # skip closing ```
            code_content = "\n".join(code_lines)
            lang_label = f'<span class="code-lang">{html.escape(lang)}</span>' if lang else ""
            html_parts.append(
                f'<div class="code-block">{lang_label}'
                f'<button class="copy-btn" onclick="copyCode(this)" title="Copy to clipboard">Copy</button>'
                f"<pre><code{lang_attr}>{code_content}</code></pre></div>"
            )
            continue

        # Table
        if "|" in stripped and stripped.startswith("|"):
            close_list()
            table_rows = []
            while i < len(lines) and "|" in lines[i].strip() and lines[i].strip().startswith("|"):
                row = lines[i].strip()
                cells = [c.strip() for c in row.split("|")[1:-1]]
                table_rows.append(cells)
                i += 1

            if len(table_rows) >= 2:
                # Check if row 1 is separator
                is_separator = all(
                    re.match(r"^[-:]+$", c.strip()) for c in table_rows[1]
                )
                if is_separator:
                    header = table_rows[0]
                    body = table_rows[2:]
                    t = '<div class="table-wrap"><table><thead><tr>'
                    for cell in header:
                        t += f"<th>{inline_format(cell)}</th>"
                    t += "</tr></thead><tbody>"
                    for row in body:
                        t += "<tr>"
                        for cell in row:
                            t += f"<td>{inline_format(cell)}</td>"
                        t += "</tr>"
                    t += "</tbody></table></div>"
                    html_parts.append(t)
                else:
                    # No header separator, treat as plain table
                    t = '<div class="table-wrap"><table><tbody>'
                    for row in table_rows:
                        t += "<tr>"
                        for cell in row:
                            t += f"<td>{inline_format(cell)}</td>"
                        t += "</tr>"
                    t += "</tbody></table></div>"
                    html_parts.append(t)
            continue

        # Heading
        heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading_match:
            close_list()
            level = len(heading_match.group(1))
            text = inline_format(heading_match.group(2))
            slug = re.sub(r"[^a-z0-9]+", "-", heading_match.group(2).lower()).strip("-")
            collapsible = ' class="collapsible"' if level == 2 else ""
            html_parts.append(f"<h{level}{collapsible} id=\"{slug}\">{text}</h{level}>")
            if level == 2:
                html_parts.append('<div class="collapsible-content">')
                # Find where this section ends (next h2 or h1, or EOF)
                j = i + 1
                depth = 0
                while j < len(lines):
                    next_stripped = lines[j].strip()
                    next_heading = re.match(r"^(#{1,2})\s+", next_stripped)
                    if next_heading and len(next_heading.group(1)) <= 2:
                        break
                    j += 1
                # We will close the div when we hit the next h2/h1 or EOF
                # Actually, let's track it differently to avoid complexity
                # We'll close in a post-processing step
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}$", stripped):
            close_list()
            html_parts.append("<hr>")
            i += 1
            continue

        # Blockquote
        if stripped.startswith(">"):
            close_list()
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote_text = re.sub(r"^>\s?", "", lines[i].strip())
                quote_lines.append(inline_format(quote_text))
                i += 1
            html_parts.append(
                f'<blockquote><p>{"<br>".join(quote_lines)}</p></blockquote>'
            )
            continue

        # Unordered list
        ul_match = re.match(r"^(\s*)[-*+]\s+(.+)$", stripped if not line.startswith(" ") else line)
        if not ul_match:
            ul_match = re.match(r"^(\s*)[-*+]\s+(.+)$", line)
        if re.match(r"^\s*[-*+]\s+", line):
            if in_list != "ul":
                close_list()
                in_list = "ul"
                html_parts.append("<ul>")
            content = re.sub(r"^\s*[-*+]\s+", "", line).strip()
            # Task list
            if content.startswith("[ ] "):
                content = f'<input type="checkbox" disabled> {inline_format(content[4:])}'
            elif content.startswith("[x] ") or content.startswith("[X] "):
                content = f'<input type="checkbox" disabled checked> {inline_format(content[4:])}'
            else:
                content = inline_format(content)
            html_parts.append(f"<li>{content}</li>")
            i += 1
            continue

        # Ordered list
        if re.match(r"^\s*\d+[.)]\s+", line):
            if in_list != "ol":
                close_list()
                in_list = "ol"
                html_parts.append("<ol>")
            content = re.sub(r"^\s*\d+[.)]\s+", "", line).strip()
            html_parts.append(f"<li>{inline_format(content)}</li>")
            i += 1
            continue

        # Paragraph
        close_list()
        para_lines = []
        while i < len(lines):
            s = lines[i].strip()
            if not s:
                break
            if s.startswith("#") or s.startswith("```") or s.startswith("|") or s.startswith(">"):
                break
            if re.match(r"^\s*[-*+]\s+", lines[i]) or re.match(r"^\s*\d+[.)]\s+", lines[i]):
                break
            if re.match(r"^[-*_]{3,}$", s):
                break
            para_lines.append(s)
            i += 1
        if para_lines:
            text = " ".join(para_lines)
            html_parts.append(f"<p>{inline_format(text)}</p>")
        continue

    close_list()

    result = "\n".join(html_parts)

    # Post-process: handle collapsible sections
    # Close collapsible-content divs before each h2 or at end
    # We need a smarter approach: use regex to insert closing divs
    parts = result.split('<div class="collapsible-content">')
    if len(parts) > 1:
        new_parts = [parts[0]]
        for idx, part in enumerate(parts[1:]):
            # Find the next collapsible heading or end
            # The content of this section is everything until the next h2.collapsible
            # or the end of the document
            next_h2_pos = part.find('<h2 class="collapsible"')
            if next_h2_pos >= 0:
                section_content = part[:next_h2_pos]
                remainder = part[next_h2_pos:]
                new_parts.append(
                    '<div class="collapsible-content">' + section_content + "</div>" + remainder
                )
            else:
                new_parts.append('<div class="collapsible-content">' + part + "</div>")
        result = "".join(new_parts)

    return result


def extract_title(md_text):
    """Extract the first H1 heading as the tutorial title."""
    match = re.match(r"^#\s+(.+)$", md_text.strip(), re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Untitled"


def build_tutorials():
    """Read all tutorials and return structured data."""
    tutorials = []
    for cat in CATEGORIES:
        for fname in cat["files"]:
            fpath = os.path.join(TUTORIALS_DIR, cat["id"], fname)
            if not os.path.exists(fpath):
                print(f"WARNING: {fpath} not found, skipping")
                continue
            with open(fpath, "r", encoding="utf-8") as f:
                md_text = f.read()

            title = extract_title(md_text)
            slug = fname.replace(".md", "")
            path = f"{cat['id']}/{slug}"
            reading_time = estimate_reading_time(md_text)
            content_html = md_to_html(md_text)

            tutorials.append(
                {
                    "path": path,
                    "title": title,
                    "category_id": cat["id"],
                    "category_title": cat["title"],
                    "reading_time": reading_time,
                    "html": content_html,
                    "plain_text": md_text,  # for search indexing
                }
            )
    return tutorials


def build_search_index(tutorials):
    """Build a lightweight search index."""
    index = []
    for t in tutorials:
        # Strip HTML for plain text search
        plain = re.sub(r"<[^>]+>", "", t["html"])
        plain = html.unescape(plain)
        # Collapse whitespace
        plain = re.sub(r"\s+", " ", plain).strip()
        index.append(
            {
                "path": t["path"],
                "title": t["title"],
                "text": plain[:5000],  # cap for file size
            }
        )
    return index


def generate_html(tutorials, search_index):
    """Generate the complete HTML file."""

    # Build sidebar nav HTML
    sidebar_items = []
    for cat in CATEGORIES:
        cat_tutorials = [t for t in tutorials if t["category_id"] == cat["id"]]
        items_html = ""
        for t in cat_tutorials:
            items_html += (
                f'<a class="nav-item" href="#{t["path"]}" data-path="{t["path"]}">'
                f'<span class="nav-check" id="check-{t["path"].replace("/", "-")}"></span>'
                f'{html.escape(t["title"])}</a>\n'
            )
        sidebar_items.append(
            f'<div class="nav-category">'
            f'<div class="nav-category-title">{cat["icon"]} {cat["title"]}</div>'
            f'<div class="nav-category-items">{items_html}</div>'
            f"</div>"
        )
    sidebar_html = "\n".join(sidebar_items)

    # Build tutorial content divs
    content_divs = []
    for t in tutorials:
        content_divs.append(
            f'<div class="tutorial-content" data-path="{t["path"]}" style="display:none;">'
            f'<div class="reading-time">{t["reading_time"]} min read</div>'
            f'{t["html"]}'
            f"</div>"
        )
    content_html = "\n".join(content_divs)

    # Serialize search index as JS
    search_js = json.dumps(search_index, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ApexAurum SensorHead Tutorials</title>
<style>
/* === RESET === */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}

/* === CSS VARIABLES === */
:root{{
  --bg:#0a0a0a;
  --surface:#1a1a1a;
  --border:#2a2a2a;
  --gold:#D4A849;
  --gold-dim:#9e7a30;
  --text:#e0e0e0;
  --text-sec:#888888;
  --text-muted:#666666;
  --code-bg:#111111;
  --code-border:#333333;
  --font:Menlo,Monaco,Consolas,'Courier New',monospace;
  --sidebar-w:280px;
  --topbar-h:52px;
}}

/* === LIGHT THEME === */
.light{{
  --bg:#f5f2ed;
  --surface:#ffffff;
  --border:#d4d0c8;
  --gold:#9e7520;
  --gold-dim:#7a5a18;
  --text:#1a1a1a;
  --text-sec:#555555;
  --text-muted:#888888;
  --code-bg:#f0ede6;
  --code-border:#c8c4bc;
}}

/* === BASE === */
html{{font-size:15px;scroll-behavior:smooth}}
body{{
  font-family:var(--font);
  background:var(--bg);
  color:var(--text);
  line-height:1.7;
  min-height:100vh;
  display:flex;
  flex-direction:column;
}}

a{{color:var(--gold);text-decoration:none}}
a:hover{{text-decoration:underline}}

/* === TOPBAR === */
.topbar{{
  position:fixed;top:0;left:0;right:0;
  height:var(--topbar-h);
  background:var(--surface);
  border-bottom:1px solid var(--border);
  display:flex;align-items:center;
  padding:0 16px;gap:12px;
  z-index:100;
}}
.topbar-title{{
  color:var(--gold);font-size:14px;font-weight:700;
  white-space:nowrap;letter-spacing:0.5px;
}}
.topbar-search{{
  flex:1;max-width:340px;margin-left:auto;
}}
.topbar-search input{{
  width:100%;padding:6px 10px;
  background:var(--bg);color:var(--text);
  border:1px solid var(--border);border-radius:4px;
  font-family:var(--font);font-size:13px;
  outline:none;
}}
.topbar-search input:focus{{border-color:var(--gold)}}
.topbar-search input::placeholder{{color:var(--text-muted)}}
.theme-toggle{{
  background:none;border:1px solid var(--border);
  color:var(--text-sec);cursor:pointer;
  padding:4px 10px;border-radius:4px;
  font-family:var(--font);font-size:12px;
}}
.theme-toggle:hover{{border-color:var(--gold);color:var(--gold)}}
.hamburger{{
  display:none;background:none;border:none;
  color:var(--text);font-size:22px;cursor:pointer;
  padding:4px 8px;
}}

/* === SIDEBAR === */
.sidebar{{
  position:fixed;top:var(--topbar-h);left:0;bottom:0;
  width:var(--sidebar-w);
  background:var(--surface);
  border-right:1px solid var(--border);
  overflow-y:auto;
  padding:12px 0;
  z-index:90;
  transition:transform 0.25s ease;
}}
.sidebar::-webkit-scrollbar{{width:4px}}
.sidebar::-webkit-scrollbar-track{{background:transparent}}
.sidebar::-webkit-scrollbar-thumb{{background:var(--border);border-radius:2px}}

.nav-category{{margin-bottom:8px}}
.nav-category-title{{
  padding:8px 16px 4px;
  font-size:11px;font-weight:700;
  color:var(--gold);
  text-transform:uppercase;
  letter-spacing:1px;
}}
.nav-item{{
  display:flex;align-items:center;gap:6px;
  padding:6px 16px 6px 20px;
  color:var(--text-sec);font-size:13px;
  text-decoration:none;
  border-left:2px solid transparent;
  transition:all 0.15s;
}}
.nav-item:hover{{
  color:var(--text);background:var(--bg);
  text-decoration:none;
}}
.nav-item.active{{
  color:var(--gold);border-left-color:var(--gold);
  background:var(--bg);
}}
.nav-item.search-hidden{{display:none}}
.nav-check{{
  font-size:11px;width:14px;
  color:var(--gold);opacity:0;
}}
.nav-check.done{{opacity:1}}
.nav-check::before{{content:"\\2713"}}

/* === OVERLAY for mobile === */
.sidebar-overlay{{
  display:none;position:fixed;
  top:var(--topbar-h);left:0;right:0;bottom:0;
  background:rgba(0,0,0,0.5);z-index:85;
}}

/* === MAIN === */
.main{{
  margin-left:var(--sidebar-w);
  margin-top:var(--topbar-h);
  padding:32px 40px 80px;
  max-width:860px;
  flex:1;
}}

/* === WELCOME === */
.welcome{{
  display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  min-height:60vh;text-align:center;
}}
.welcome h1{{color:var(--gold);font-size:22px;margin-bottom:12px}}
.welcome p{{color:var(--text-sec);font-size:14px;max-width:480px;line-height:1.8}}

/* === READING TIME === */
.reading-time{{
  color:var(--text-muted);font-size:12px;
  margin-bottom:20px;padding-bottom:12px;
  border-bottom:1px solid var(--border);
}}

/* === TYPOGRAPHY === */
.tutorial-content h1{{
  color:var(--gold);font-size:22px;
  margin:0 0 16px;padding-bottom:8px;
  border-bottom:1px solid var(--border);
}}
.tutorial-content h2{{
  color:var(--gold);font-size:17px;
  margin:28px 0 12px;cursor:pointer;
  padding:6px 0;
  user-select:none;
  position:relative;
}}
.tutorial-content h2.collapsible::after{{
  content:"\\25BE";position:absolute;right:0;
  font-size:14px;color:var(--text-muted);
  transition:transform 0.2s;
}}
.tutorial-content h2.collapsed::after{{
  transform:rotate(-90deg);
}}
.tutorial-content h3{{
  color:var(--text);font-size:15px;
  margin:20px 0 8px;font-weight:700;
}}
.tutorial-content h4{{
  color:var(--text-sec);font-size:14px;
  margin:16px 0 6px;font-weight:700;
}}
.tutorial-content p{{margin:0 0 12px;font-size:14px}}
.tutorial-content hr{{
  border:none;border-top:1px solid var(--border);
  margin:24px 0;
}}

/* === LISTS === */
.tutorial-content ul,.tutorial-content ol{{
  margin:0 0 12px;padding-left:24px;
}}
.tutorial-content li{{
  margin-bottom:4px;font-size:14px;
}}
.tutorial-content li input[type="checkbox"]{{
  margin-right:6px;accent-color:var(--gold);
}}

/* === BLOCKQUOTE === */
.tutorial-content blockquote{{
  border-left:3px solid var(--gold);
  background:var(--code-bg);
  padding:10px 16px;margin:12px 0;
  border-radius:0 4px 4px 0;
}}
.tutorial-content blockquote p{{
  margin:0;color:var(--text-sec);font-size:13px;
}}

/* === CODE === */
.tutorial-content code{{
  background:var(--code-bg);
  border:1px solid var(--code-border);
  padding:1px 5px;border-radius:3px;
  font-size:13px;color:var(--gold);
}}
.code-block{{
  position:relative;margin:12px 0;
  background:var(--code-bg);
  border:1px solid var(--code-border);
  border-radius:4px;overflow:hidden;
}}
.code-block pre{{
  padding:14px 16px;overflow-x:auto;margin:0;
}}
.code-block pre code{{
  background:none;border:none;padding:0;
  color:var(--text);font-size:13px;
  line-height:1.5;display:block;
}}
.code-lang{{
  position:absolute;top:6px;right:70px;
  font-size:10px;color:var(--text-muted);
  text-transform:uppercase;letter-spacing:0.5px;
}}
.copy-btn{{
  position:absolute;top:6px;right:8px;
  background:var(--border);color:var(--text-sec);
  border:none;padding:2px 10px;border-radius:3px;
  font-family:var(--font);font-size:11px;
  cursor:pointer;opacity:0;transition:opacity 0.15s;
}}
.code-block:hover .copy-btn{{opacity:1}}
.copy-btn:hover{{background:var(--gold);color:var(--bg)}}
.copy-btn.copied{{background:var(--gold);color:var(--bg)}}

/* === TABLES === */
.table-wrap{{
  overflow-x:auto;margin:12px 0;
  border:1px solid var(--border);border-radius:4px;
}}
.tutorial-content table{{
  width:100%;border-collapse:collapse;
  font-size:13px;
}}
.tutorial-content th{{
  background:var(--gold-dim);color:var(--bg);
  padding:8px 12px;text-align:left;
  font-weight:700;white-space:nowrap;
}}
.light .tutorial-content th{{
  background:var(--gold);color:#fff;
}}
.tutorial-content td{{
  padding:8px 12px;border-top:1px solid var(--border);
}}
.tutorial-content tr:nth-child(even) td{{
  background:rgba(212,168,73,0.04);
}}

/* === COLLAPSIBLE === */
.collapsible-content{{
  overflow:hidden;
  transition:max-height 0.3s ease;
}}
.collapsible-content.collapsed{{
  max-height:0 !important;
  overflow:hidden;
}}

/* === SEARCH HIGHLIGHT === */
mark{{
  background:rgba(212,168,73,0.35);
  color:inherit;padding:0 2px;border-radius:2px;
}}

/* === SCROLL TO TOP === */
.scroll-top{{
  position:fixed;bottom:70px;right:24px;
  width:38px;height:38px;
  background:var(--surface);border:1px solid var(--border);
  color:var(--gold);font-size:18px;
  border-radius:50%;cursor:pointer;
  display:none;align-items:center;justify-content:center;
  z-index:80;transition:opacity 0.2s;
  font-family:var(--font);
}}
.scroll-top:hover{{background:var(--gold);color:var(--bg);border-color:var(--gold)}}
.scroll-top.visible{{display:flex}}

/* === FOOTER === */
.footer{{
  text-align:center;padding:16px;
  color:var(--text-muted);font-size:11px;
  border-top:1px solid var(--border);
  margin-left:var(--sidebar-w);
}}
.footer em{{color:var(--gold-dim);font-style:italic}}

/* === MOBILE === */
@media(max-width:768px){{
  .hamburger{{display:block}}
  .sidebar{{transform:translateX(-100%)}}
  .sidebar.open{{transform:translateX(0)}}
  .sidebar-overlay.open{{display:block}}
  .main{{margin-left:0;padding:20px 16px 80px}}
  .footer{{margin-left:0}}
  .topbar-title{{font-size:12px}}
  .topbar-search{{max-width:180px}}
}}

/* === PRINT === */
@media print{{
  .topbar,.sidebar,.sidebar-overlay,.scroll-top,.footer,
  .copy-btn,.code-lang,.theme-toggle,.hamburger,
  .topbar-search,.reading-time{{display:none !important}}
  .main{{
    margin:0;padding:20px;max-width:none;
    color:#000;background:#fff;
  }}
  .tutorial-content{{display:block !important}}
  .tutorial-content h1,.tutorial-content h2,
  .tutorial-content h3{{color:#000}}
  .tutorial-content code{{
    background:#f0f0f0;color:#333;border-color:#ccc;
  }}
  .code-block{{background:#f5f5f5;border-color:#ccc}}
  .code-block pre code{{color:#000}}
  .tutorial-content th{{background:#ddd;color:#000}}
  .tutorial-content blockquote{{
    border-left-color:#999;background:#f9f9f9;
  }}
  .tutorial-content blockquote p{{color:#333}}
  a{{color:#333}}
  .collapsible-content{{
    max-height:none !important;overflow:visible !important;
  }}
}}
</style>
</head>
<body>

<!-- TOPBAR -->
<div class="topbar">
  <button class="hamburger" onclick="toggleSidebar()" aria-label="Toggle menu">&#9776;</button>
  <div class="topbar-title">ApexAurum SensorHead Tutorials</div>
  <div class="topbar-search">
    <input type="text" id="search-input" placeholder="Search tutorials..." oninput="onSearch(this.value)">
  </div>
  <button class="theme-toggle" onclick="toggleTheme()" id="theme-btn">Light</button>
</div>

<!-- SIDEBAR OVERLAY (mobile) -->
<div class="sidebar-overlay" id="sidebar-overlay" onclick="toggleSidebar()"></div>

<!-- SIDEBAR -->
<nav class="sidebar" id="sidebar">
{sidebar_html}
</nav>

<!-- MAIN CONTENT -->
<div class="main" id="main">
  <div class="welcome" id="welcome">
    <h1>SensorHead Tutorials</h1>
    <p>22 guides covering setup, configuration, and deep dives into the ApexAurum SensorHead system. Select a tutorial from the sidebar to begin.</p>
  </div>
{content_html}
</div>

<!-- SCROLL TO TOP -->
<button class="scroll-top" id="scroll-top" onclick="scrollToTop()">&#8593;</button>

<!-- FOOTER -->
<div class="footer">
  <em>"The Athanor's flame lights the way."</em> &mdash; ApexAurum v1.0
</div>

<script>
/* === DATA === */
var SEARCH_INDEX = {search_js};

/* === STATE === */
var currentPath = null;

/* === NAVIGATION === */
function navigate(path) {{
  // Hide all tutorials
  var all = document.querySelectorAll('.tutorial-content');
  for (var i = 0; i < all.length; i++) all[i].style.display = 'none';
  document.getElementById('welcome').style.display = 'none';

  // Show target
  var target = document.querySelector('.tutorial-content[data-path="' + path + '"]');
  if (target) {{
    target.style.display = 'block';
    currentPath = path;
    // Mark as read
    markRead(path);
    // Update nav active
    var navItems = document.querySelectorAll('.nav-item');
    for (var i = 0; i < navItems.length; i++) {{
      navItems[i].classList.toggle('active', navItems[i].getAttribute('data-path') === path);
    }}
    // Scroll to top of content
    window.scrollTo(0, 0);
    // Close sidebar on mobile
    if (window.innerWidth <= 768) {{
      document.getElementById('sidebar').classList.remove('open');
      document.getElementById('sidebar-overlay').classList.remove('open');
    }}
  }} else {{
    document.getElementById('welcome').style.display = 'flex';
  }}
}}

/* === HASH ROUTING === */
function handleHash() {{
  var hash = window.location.hash.replace('#', '');
  if (hash) {{
    navigate(hash);
  }} else {{
    // Show welcome
    var all = document.querySelectorAll('.tutorial-content');
    for (var i = 0; i < all.length; i++) all[i].style.display = 'none';
    document.getElementById('welcome').style.display = 'flex';
    currentPath = null;
    var navItems = document.querySelectorAll('.nav-item');
    for (var i = 0; i < navItems.length; i++) navItems[i].classList.remove('active');
  }}
}}
window.addEventListener('hashchange', handleHash);

/* === SIDEBAR TOGGLE (mobile) === */
function toggleSidebar() {{
  var sb = document.getElementById('sidebar');
  var ov = document.getElementById('sidebar-overlay');
  sb.classList.toggle('open');
  ov.classList.toggle('open');
}}

/* === THEME TOGGLE === */
function toggleTheme() {{
  var isLight = document.body.classList.toggle('light');
  document.getElementById('theme-btn').textContent = isLight ? 'Dark' : 'Light';
  try {{ localStorage.setItem('aa-theme', isLight ? 'light' : 'dark'); }} catch(e) {{}}
}}
function loadTheme() {{
  try {{
    if (localStorage.getItem('aa-theme') === 'light') {{
      document.body.classList.add('light');
      document.getElementById('theme-btn').textContent = 'Dark';
    }}
  }} catch(e) {{}}
}}

/* === SEARCH === */
function onSearch(query) {{
  query = query.toLowerCase().trim();
  var navItems = document.querySelectorAll('.nav-item');

  if (!query) {{
    for (var i = 0; i < navItems.length; i++) {{
      navItems[i].classList.remove('search-hidden');
    }}
    // Remove highlights
    removeHighlights();
    return;
  }}

  // Filter sidebar
  for (var i = 0; i < navItems.length; i++) {{
    var path = navItems[i].getAttribute('data-path');
    var entry = null;
    for (var j = 0; j < SEARCH_INDEX.length; j++) {{
      if (SEARCH_INDEX[j].path === path) {{ entry = SEARCH_INDEX[j]; break; }}
    }}
    if (entry) {{
      var match = entry.title.toLowerCase().indexOf(query) >= 0 ||
                  entry.text.toLowerCase().indexOf(query) >= 0;
      navItems[i].classList.toggle('search-hidden', !match);
    }}
  }}

  // Highlight in current content
  if (currentPath) {{
    highlightInContent(query);
  }}
}}

function highlightInContent(query) {{
  removeHighlights();
  if (!query) return;
  var content = document.querySelector('.tutorial-content[data-path="' + currentPath + '"]');
  if (!content) return;
  walkTextNodes(content, query);
}}

function walkTextNodes(node, query) {{
  if (node.nodeType === 3) {{ // text node
    var text = node.textContent;
    var lower = text.toLowerCase();
    var idx = lower.indexOf(query);
    if (idx >= 0) {{
      var before = text.substring(0, idx);
      var match = text.substring(idx, idx + query.length);
      var after = text.substring(idx + query.length);
      var span = document.createElement('span');
      span.innerHTML = escapeHtml(before) + '<mark>' + escapeHtml(match) + '</mark>' + escapeHtml(after);
      span.className = 'search-result-wrap';
      node.parentNode.replaceChild(span, node);
    }}
  }} else if (node.nodeType === 1 && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE' &&
             node.tagName !== 'CODE' && node.tagName !== 'PRE' && node.tagName !== 'MARK') {{
    var children = Array.prototype.slice.call(node.childNodes);
    for (var i = 0; i < children.length; i++) {{
      walkTextNodes(children[i], query);
    }}
  }}
}}

function removeHighlights() {{
  var marks = document.querySelectorAll('.search-result-wrap');
  for (var i = 0; i < marks.length; i++) {{
    var parent = marks[i].parentNode;
    parent.replaceChild(document.createTextNode(marks[i].textContent), marks[i]);
    parent.normalize();
  }}
}}

function escapeHtml(text) {{
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(text));
  return div.innerHTML;
}}

/* === CODE COPY === */
function copyCode(btn) {{
  var block = btn.closest('.code-block');
  var code = block.querySelector('code');
  var text = code.textContent;
  if (navigator.clipboard) {{
    navigator.clipboard.writeText(text).then(function() {{
      btn.textContent = 'Copied';
      btn.classList.add('copied');
      setTimeout(function() {{
        btn.textContent = 'Copy';
        btn.classList.remove('copied');
      }}, 1500);
    }});
  }} else {{
    // Fallback
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try {{ document.execCommand('copy');
      btn.textContent = 'Copied';
      btn.classList.add('copied');
      setTimeout(function() {{
        btn.textContent = 'Copy';
        btn.classList.remove('copied');
      }}, 1500);
    }} catch(e) {{}}
    document.body.removeChild(ta);
  }}
}}

/* === COLLAPSIBLE SECTIONS === */
function initCollapsible() {{
  var headings = document.querySelectorAll('h2.collapsible');
  for (var i = 0; i < headings.length; i++) {{
    headings[i].addEventListener('click', function() {{
      this.classList.toggle('collapsed');
      var content = this.nextElementSibling;
      if (content && content.classList.contains('collapsible-content')) {{
        content.classList.toggle('collapsed');
      }}
    }});
  }}
}}

/* === PROGRESS TRACKING === */
function markRead(path) {{
  try {{
    var read = JSON.parse(localStorage.getItem('aa-read') || '[]');
    if (read.indexOf(path) < 0) {{
      read.push(path);
      localStorage.setItem('aa-read', JSON.stringify(read));
    }}
    updateChecks();
  }} catch(e) {{}}
}}

function updateChecks() {{
  try {{
    var read = JSON.parse(localStorage.getItem('aa-read') || '[]');
    var checks = document.querySelectorAll('.nav-check');
    for (var i = 0; i < checks.length; i++) {{
      var id = checks[i].id.replace('check-', '').replace(/-/g, '/');
      // Reconstruct path: first segment is category, rest is slug
      // id format: quick-start-01-first-boot -> quick-start/01-first-boot
      // We need to be smarter about the split
      checks[i].classList.toggle('done', read.indexOf(id) >= 0);
    }}
  }} catch(e) {{}}
}}

/* Proper ID to path mapping */
function fixCheckIds() {{
  var navItems = document.querySelectorAll('.nav-item');
  for (var i = 0; i < navItems.length; i++) {{
    var path = navItems[i].getAttribute('data-path');
    var check = navItems[i].querySelector('.nav-check');
    if (check) {{
      check.id = 'check-' + path;
    }}
  }}
}}

/* === SCROLL TO TOP === */
function scrollToTop() {{
  window.scrollTo({{ top: 0, behavior: 'smooth' }});
}}

window.addEventListener('scroll', function() {{
  var btn = document.getElementById('scroll-top');
  btn.classList.toggle('visible', window.scrollY > 400);
}});

/* === INIT === */
window.addEventListener('DOMContentLoaded', function() {{
  loadTheme();
  fixCheckIds();
  updateChecks();
  initCollapsible();
  handleHash();
}});
</script>
</body>
</html>"""


def main():
    print("Building tutorial viewer...")
    tutorials = build_tutorials()
    print(f"  Loaded {len(tutorials)} tutorials")

    search_index = build_search_index(tutorials)
    print(f"  Built search index ({len(search_index)} entries)")

    html_output = generate_html(tutorials, search_index)
    print(f"  Generated HTML ({len(html_output)} bytes)")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_output)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"  Written to {OUTPUT_FILE}")
    print(f"  File size: {size_kb:.1f} KB")

    if size_kb > 1024:
        print("  WARNING: File exceeds 1MB target")
    elif size_kb > 500:
        print("  NOTE: File exceeds 500KB ideal target but is under 1MB")
    else:
        print("  File size is within ideal target")


if __name__ == "__main__":
    main()
