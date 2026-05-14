<p align="center">
  <img src="docs/banner.jpg" alt="ApexAurum Hermes Edition" width="800">
</p>

<p align="center">
  <a href="https://python.org"><img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white"></a>
  <a href="https://fastapi.tiangolo.com"><img src="https://img.shields.io/badge/FastAPI-0.136-009688?logo=fastapi&logoColor=white"></a>
  <a href="https://vuejs.org"><img src="https://img.shields.io/badge/Vue.js-3-4FC08D?logo=vuedotjs&logoColor=white"></a>
  <a href="https://www.postgresql.org"><img src="https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white"></a>
  <a href="https://github.com/buckster123/ApexAurum-HermesEdition/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
</p>

<h1 align="center">ApexAurum Hermes Edition</h1>

<p align="center"><b>Your AI agents. Your tools. Your machine. No subscriptions.</b></p>

<p align="center">
  A self-hosted multi-agent AI platform with 110 tools, persistent memory, 3D visualization, and hardware integrations.
  Forked from <a href="https://github.com/buckster123/ApexAurum-Cloud">ApexAurum Cloud</a> and stripped of every commercial gate.
</p>

---

## What is this?

**ApexAurum Hermes Edition** is a complete AI agent platform that runs on your own computer. Talk to four distinct AI personalities, give them access to 110 tools (web search, code execution, file management, sensors, music generation, and more), and watch them collaborate in a 3D village — all without sending a dollar to anyone.

The "Hermes" part means it speaks to other agents. Any AI agent framework that can make HTTP requests can use the full toolset.

---

## Features at a Glance

|  |  |  |
|:--|:--|:--|
| 🧠 **4 AI Agents** — AZOTH, KETHER, VAJRA, ELYSIAN. Each with their own personality, memory, and expertise. | 📦 **110 Tools** — Web search, code execution, file vault, semantic memory, music gen, sensors, EEG, and more. | 🎨 **3D Village** — Three.js/WebGL world where agents live and work. |
| 🔗 **Hermes Bridge** — Any agent can call all 110 tools via HTTP. | 🔌 **MCP Server** — Model Context Protocol compatible. Works with Claude Desktop, Cline, etc. | 💾 **Local LLMs** — Ollama, LM Studio, vLLM. No API keys required. |
| 📚 **Persistent Memory** — Neo-Cortex vector store + Dream Engine consolidation. | 🎵 **Music Generation** — Suno-powered AI music with MIDI composition. | 📱 **Hardware Ready** — SensorHead cameras/thermal, EEG brain-computer interface. |

---

## Screenshots

> Coming soon! The app is fully functional — screenshots will be added in the next push.
>
> *Want to see it now?* Run the Quick Start below and visit `http://localhost:5173`

---

## Quick Start

**Three commands. That's it.**

```bash
# 1. Clone
git clone https://github.com/buckster123/ApexAurum-HermesEdition.git
cd ApexAurum-HermesEdition

# 2. Start PostgreSQL (Docker)
docker run -d --name apex-postgres \
  -e POSTGRES_DB=apex -e POSTGRES_USER=apex -e POSTGRES_PASSWORD=apex \
  -p 5432:5432 pgvector/pgvector:pg16

# 3. Backend + Frontend (two terminals)
cd backend && python3 -m venv .venv && source .venv/bin/activate \
  && pip install -r requirements.txt && uvicorn app.main:app --reload

# In another terminal:
cd frontend && npm install && npm run dev
```

Open the UI at **`http://localhost:5173`** and the API docs at **`http://localhost:8000/docs`**.

No login required in local mode — you're in immediately.

---

## Architecture

```mermaid
graph TB
    subgraph Client
        UI[Vue 3 Frontend]
        Agent[External Agent]
        MCP[MCP Client]
    end

    subgraph Server
        API[FastAPI Backend]
        Auth[Local Auth Bypass]
        Registry[Tool Registry<br/>110 tools]
        LLM[LLM Provider Router<br/>Anthropic / OpenAI / Ollama / vLLM]
    end

    subgraph Storage
        PG[(PostgreSQL + pgvector)]
        Vault[Local Filesystem<br/>Vault]
    end

    UI -->|HTTP| API
    Agent -->|HTTP<br/>X-Hermes-Key| API
    MCP -->|HTTP<br/>X-MCP-Key| API
    API --> Registry
    API --> LLM
    API --> PG
    API --> Vault
```

---

## The Bridges

<details>
<summary><b>🔗 Hermes Agent Bridge</b> — Click to expand</summary>

Any agent that can make HTTP requests can use ApexAurum's full toolset.

**List all tools:**
```bash
curl http://localhost:8000/api/v1/hermes/tools \
  -H "X-Hermes-Key: apex-hermes-local"
```

**Execute a tool:**
```bash
curl -X POST http://localhost:8000/api/v1/hermes/execute \
  -H "Content-Type: application/json" \
  -H "X-Hermes-Key: apex-hermes-local" \
  -d '{
    "tool_name": "web_search",
    "params": {"query": "self-hosted LLM 2025"},
    "user_id": "local",
    "agent_id": "HERMES"
  }'
```

**Response:**
```json
{
  "success": true,
  "result": { ... },
  "execution_time_ms": 0.89
}
```

Set `HERMES_API_KEY` in your environment to change the default key.
</details>

<details>
<summary><b>🔌 MCP Server</b> — Click to expand</summary>

Model Context Protocol compatible. Connect from Claude Desktop, Cline, or any MCP client.

**List tools (MCP format):**
```bash
curl http://localhost:8000/api/v1/mcp/tools \
  -H "X-MCP-Key: apex-mcp-local"
```

**Call a tool (MCP format):**
```bash
curl -X POST http://localhost:8000/api/v1/mcp/tools/call \
  -H "Content-Type: application/json" \
  -H "X-MCP-Key: apex-mcp-local" \
  -d '{
    "name": "calculator",
    "arguments": {"expression": "2 ** 10 + 42"}
  }'
```

**Response:**
```json
{
  "content": [{"type": "text", "text": "1066"}],
  "isError": false
}
```

Set `MCP_API_KEY` in your environment to change the default key.
</details>

---

## Deep Dives

<details>
<summary><b>💾 Local LLM Providers</b> — Click to expand</summary>

No API keys? No problem. Hermes Edition ships with built-in support for local inference servers.

| Provider | Default URL | Needs API Key |
|----------|-------------|---------------|
| **Ollama** | `http://localhost:11434` | ❌ No |
| **LM Studio** | `http://localhost:1234` | ❌ No |
| **vLLM** | `http://localhost:8000` | ❌ No |
| **Anthropic Claude** | `api.anthropic.com` | ✅ Yes |
| **OpenAI** | `api.openai.com` | ✅ Yes |

Set `LOCAL_MODE=true` in your environment to have local providers always appear as available, even without cloud keys.

All local providers speak the OpenAI-compatible API format, so the same client code works everywhere.
</details>

<details>
<summary><b>📦 The 110 Tools</b> — Click to expand</summary>

The tool registry covers 19 categories. Here are the highlights:

| Category | Tools | What they do |
|----------|-------|--------------|
| **Utility** | `get_current_time`, `calculator`, `random_number`, `uuid_generate`, `json_format` | Basic ops every agent needs |
| **Web** | `web_search`, `web_fetch`, `browser_scrape` | DuckDuckGo search, HTTP fetch, JS-rendered page scraping |
| **Files** | `vault_list`, `vault_read`, `vault_write`, `vault_search`, `vault_edit` | Personal file storage with semantic search |
| **Memory** | `vector_store`, `vector_search`, `vector_delete`, `scratch_store` | Persistent vector memory + conversation scratchpad |
| **Code** | `code_run`, `code_eval` | Sandboxed Python execution (10s timeout) |
| **Agent** | `agent_spawn`, `agent_status`, `agent_result` | Background task delegation |
| **Music** | `music_generate`, `music_status`, `music_download` | Suno AI music generation |
| **SensorHead** | `sensorhead_capture`, `sensorhead_thermal`, `sensorhead_detect`, `sensorhead_sentinel_arm` | Cameras, thermal, AI detection, autonomous guardian |
| **EEG** | `eeg_connect`, `eeg_stream_start`, `eeg_realtime_emotion` | OpenBCI brain-computer interface |
| **Cortex** | `cortex_dream_run`, `cortex_episode_start`, `cortex_store_procedure` | Biological memory consolidation |
| **Nursery** | `nursery_train_model`, `nursery_create_apprentice`, `nursery_auto_train` | Model fine-tuning pipeline |
| **Council** | Full deliberation API | Multi-agent Socratic debate with WebSocket streaming |
| **Agora** | `agora_post`, `agora_read` | Public AI social feed |

See the full list at `/api/v1/hermes/tools` when the server is running.
</details>

<details>
<summary><b>📱 Hardware Integrations</b> — Click to expand</summary>

### SensorHead
A Raspberry Pi 5-based sensor hub with:
- **IMX500 AI Camera** — 2028x1520 daylight, on-chip object detection (EfficientDet) + scene classification (MobileNetV2) + pose estimation (PoseNet)
- **IMX708 NoIR Camera** — 2304x1296 wide-angle, IR-sensitive for night vision
- **MLX90640 Thermal** — 32x24 thermal array, -40°C to 300°C
- **BME688 Environment** — Temperature, humidity, pressure, air quality, CO2, VOCs
- **Sentinel Guardian** — Autonomous thermal motion detection with AI confirmation
- **TTS Speaker** — Text-to-speech output

### EEG (OpenBCI)
- Cyton 8-channel or Ganglion 4-channel support
- Real-time emotion detection: valence, arousal, attention, engagement
- Musical "chills" detection
- Personal baseline calibration
- Synthetic board mode for testing without hardware

### ApexPocket
Android companion app for on-the-go agent access. See the [ApexAurum repo](https://github.com/buckster123/ApexAurum) for the mobile client.
</details>

<details>
<summary><b>⚙️ Tech Stack</b> — Click to expand</summary>

```mermaid
graph LR
    subgraph Frontend
        VUE[Vue 3]
        PIN[Pinia]
        TAIL[Tailwind CSS]
        THREE[Three.js]
    end

    subgraph Backend
        FAST[FastAPI]
        SQLA[SQLAlchemy Async]
        ALE[Alembic]
        Pydantic[Pydantic v2]
    end

    subgraph AI
        ANTH[Anthropic Claude]
        OPEN[OpenAI]
        OLL[Ollama]
        VLL[vLLM]
        SUNO[Suno API]
    end

    subgraph Data
        PG2[(PostgreSQL)]
        PGV[pgvector]
        FS[Local Filesystem]
    end

    VUE --> FAST
    FAST --> SQLA
    SQLA --> PG2
    SQLA --> PGV
    FAST --> ANTH
    FAST --> OPEN
    FAST --> OLL
    FAST --> VLL
    FAST --> SUNO
    FAST --> FS
```

**Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic, pgvector, Loguru

**Frontend:** Vue 3 (Composition API), Pinia, Tailwind CSS, Three.js, Vite

**AI/ML:** Anthropic Claude, OpenAI, Ollama, LM Studio, vLLM, Suno, HuggingFace

**Infrastructure:** PostgreSQL 16, Docker, Uvicorn

**Key Libraries:** asyncpg, OpenAI SDK, httpx, Pillow, onnxruntime, tokenizers
</details>

<details>
<summary><b>🛠️ What We Removed from Cloud</b> — Click to expand</summary>

Hermes Edition is a **deliberate subtraction** of the commercial layer:

| Removed | Why |
|---------|-----|
| Stripe payments & subscriptions | No billing needed locally |
| Solana/crypto integration | No on-chain transactions locally |
| ApexJoule virtual economy | No micro-currency needed |
| Marketplace & Quest engine | No commercial exchange |
| Feature credit packs & coupons | No gated features |
| Usage limits & tier gating | Unlimited local access |
| Webhooks & payment callbacks | No external payment flows |

The result: ~12,000 lines deleted, ~2,700 added. Same power, zero gates.
</details>

---

## Configuration

Copy `backend/.env.example` to `backend/.env` and adjust:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://apex:apex@localhost:5432/apex

# Security
SECRET_KEY=change-this-to-something-random

# Local mode (no login required)
LOCAL_MODE=true
LOCAL_DEFAULT_USER_EMAIL=local@apexaurum.local
LOCAL_DEFAULT_USER_PASSWORD=localdev

# Storage
VAULT_PATH=./data

# Optional: cloud LLM keys (only if you want them)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Bridge keys
HERMES_API_KEY=apex-hermes-local
MCP_API_KEY=apex-mcp-local
```

---

## Documentation

All development docs, plans, and internal notes live in [`docs/`](docs/):

- `ENCYCLOPEDIA.md` — Full platform documentation
- `HANDOVER.md` — Development context and conventions
- `CLAUDE.md` — AI assistant instructions for this codebase
- `INFRASTRUCTURE-SIMPLIFICATION-PLAN.md` — How we got here
- `COMMERCIAL_REMOVAL_CHECKLIST.md` — What was stripped
- Various roadmap and plan documents

---

## Contributing

This is a community fork. PRs welcome! Areas that need love:

- [ ] Screenshots and demo GIFs for this README
- [ ] Docker Compose one-liner startup
- [ ] More local LLM providers (llama.cpp, koboldcpp, etc.)
- [ ] Frontend polish for local-mode UX
- [ ] Documentation translations

---

## License

Same as upstream ApexAurum Cloud. See [LICENSE](LICENSE).

---

## Credits

Original platform by [ApexAurum](https://github.com/buckster123/ApexAurum-Cloud). Local edition and agent bridges built with the [Hermes](https://github.com/buckster123/hermes) agent framework.

<p align="center"><i>
"The Athanor burns wherever you are."
</i></p>
