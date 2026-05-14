# ApexAurum Hermes Edition

**Self-hosted multi-agent AI platform with 110 tools, persistent memory, Hermes agent bridge, MCP server, and local LLM support.**

```
"The gold was always there. Now it runs on your machine."
```

Built with FastAPI + Vue 3 + PostgreSQL/pgvector. Forked from [ApexAurum Cloud](https://github.com/buckster123/ApexAurum-Cloud) and stripped of all commercial infrastructure. Run it locally, own your data, hook it into your agents.

---

## What is this?

ApexAurum Hermes Edition is the self-hosted, open-source sibling of ApexAurum Cloud. Same four AI personas (AZOTH, KETHER, VAJRA, ELYSIAN), same 110 tools, same 3D village, same persistent memory and Dream Engine — but running on your own hardware with no subscriptions, no payments, no crypto, and no cloud lock-in.

The Hermes Edition adds:
- **Hermes Agent Bridge** — exposes all 110 tools as HTTP endpoints that any agent (including Hermes itself) can call
- **MCP Server** — Model Context Protocol compatible tool server for MCP clients
- **Local LLM Providers** — Ollama, LM Studio, and vLLM out of the box
- **Zero-Auth Local Mode** — fire it up, no login required

---

## Quick Start

### Prerequisites
- Docker (for PostgreSQL)
- Python 3.11+ and Node.js 18+
- (Optional) Ollama, LM Studio, or vLLM for local LLMs

### 1. Clone & setup
```bash
git clone https://github.com/buckster123/ApexAurum-HermesEdition.git
cd ApexAurum-HermesEdition
```

### 2. Start PostgreSQL
```bash
docker run -d --name apex-postgres \
  -e POSTGRES_DB=apex \
  -e POSTGRES_USER=apex \
  -e POSTGRES_PASSWORD=apex \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 3. Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy and edit config
cp .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY, and optionally LOCAL_MODE=true

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be at `http://localhost:8000` with auto-generated docs at `/docs`.

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```

The UI will be at `http://localhost:5173`.

---

## Hermes Agent Bridge

Any agent that speaks HTTP can use ApexAurum's 110 tools.

**List tools:**
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
    "params": {"query": "local LLM setup"},
    "user_id": "local",
    "agent_id": "HERMES"
  }'
```

Set `HERMES_API_KEY` in your environment to change the default key.

---

## MCP Server

MCP-compatible clients (Claude Desktop, Cline, etc.) can connect directly.

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
    "arguments": {"expression": "2 ** 10"}
  }'
```

Set `MCP_API_KEY` in your environment to change the default key.

---

## Local LLM Providers

Configure in `backend/app/services/llm_provider.py` or via environment:

| Provider | Default URL | API Key |
|----------|-------------|---------|
| Ollama | http://localhost:11434 | not required |
| LM Studio | http://localhost:1234 | not required |
| vLLM | http://localhost:8000 | not required |
| Anthropic Claude | api.anthropic.com | required |
| OpenAI | api.openai.com | required |

Set `LOCAL_MODE=true` to have local providers always show as available.

---

## What's Included

### Core
- Streaming chat with conversation branching and model selection
- 110 tools across 19 categories (web, code, files, memory, sensors, EEG, music, etc.)
- Four AI agents with persistent personalities and PAC mode
- Multi-agent Council Deliberation with WebSocket streaming
- Personal Vault (file storage with semantic search)
- Neo-Cortex vector memory with pgvector
- CerebroCortex Dream Engine (biological memory consolidation)
- 3D Village with Three.js/WebGL
- Music generation via Suno API
- Model training pipeline (Nursery)

### Hardware Integrations
- SensorHead — cameras, thermal, environment sensors, TTS, Sentinel guardian
- EEG — OpenBCI brain-computer interface with emotion detection
- ApexPocket — Android companion app support

### Removed from Cloud → Local
- Stripe payments and subscriptions
- Solana/crypto integration
- ApexJoule virtual economy
- Marketplace and quest engine
- Feature credit packs and coupons
- Usage limits and tier gating
- All commercial billing surfaces

---

## Architecture

```
Vue 3 Frontend  <--HTTP-->  FastAPI Backend  <--SQLAlchemy-->  PostgreSQL + pgvector
                                    |
                    +---------------+---------------+
                    |                               |
            Hermes Bridge            MCP Server
            (/api/v1/hermes)         (/api/v1/mcp)
                    |                               |
            Tool Registry (110 tools)        Tool Registry
```

---

## Environment Variables

Key variables from `.env.example`:

```env
DATABASE_URL=postgresql+asyncpg://apex:apex@localhost:5432/apex
SECRET_KEY=your-secret-key-here
LOCAL_MODE=true
LOCAL_DEFAULT_USER_EMAIL=local@apexaurum.local
LOCAL_DEFAULT_USER_PASSWORD=localdev
VAULT_PATH=./data
DEBUG=true

# Optional — only if using cloud LLM providers
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Bridge keys
HERMES_API_KEY=apex-hermes-local
MCP_API_KEY=apex-mcp-local
```

---

## License

Same as upstream ApexAurum Cloud. See LICENSE file.

---

## Credits

Original platform by [ApexAurum](https://github.com/buckster123/ApexAurum-Cloud). Local edition and Hermes/MCP bridges built in collaboration with the Hermes agent framework.

```
"The Athanor burns wherever you are."
```
