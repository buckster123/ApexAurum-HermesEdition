"""
ApexAurum Cloud - API v1 Router

All API endpoints are mounted here.
"""

from fastapi import APIRouter

from app.api.v1 import auth, chat, agents, village, tools, music, user, prompts, import_data, memory, files, cortex, billing, council, admin, jam, feedback, nursery, devices, pocket, errors, agora, sensors, dream, memory_import, sentinel, app_distribution, agent_portability, multiverse, eeg, athaverse
from app.hermes.router import router as hermes_router
from app.mcp.router import router as mcp_router

router = APIRouter()

# Include sub-routers
router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
router.include_router(chat.router, prefix="/chat", tags=["Chat"])
router.include_router(agents.router, prefix="/agents", tags=["Agents"])
router.include_router(village.router, prefix="/village", tags=["Village"])
router.include_router(tools.router, prefix="/tools", tags=["Tools"])
router.include_router(music.router, prefix="/music", tags=["Music"])
router.include_router(user.router, prefix="/user", tags=["User"])
router.include_router(prompts.router, prefix="/prompts", tags=["Prompts"])
router.include_router(import_data.router, prefix="/import", tags=["Import"])
router.include_router(memory.router, prefix="/memory", tags=["Memory"])
router.include_router(files.router, prefix="/files", tags=["Files"])
router.include_router(cortex.router)  # Neo-Cortex dashboard (prefix already in cortex.py)
router.include_router(billing.router, prefix="/billing", tags=["Billing"])
router.include_router(council.router)  # Council deliberation (prefix already in council.py)
router.include_router(admin.router)  # Admin endpoints (prefix already in admin.py)
router.include_router(jam.router)  # Jam sessions (prefix already in jam.py)
router.include_router(feedback.router)  # Bug reports and feedback
router.include_router(nursery.router)  # Nursery - model training studio
router.include_router(devices.router, prefix="/devices", tags=["Devices"])
router.include_router(sensors.router, prefix="/devices", tags=["SensorHead Dashboard"])
router.include_router(eeg.router, prefix="/devices", tags=["EEG Dashboard"])
router.include_router(pocket.router, prefix="/pocket", tags=["ApexPocket"])
router.include_router(errors.router)  # Error reporting (prefix in errors.py)
router.include_router(agora.router)  # Agora - public AI social feed
router.include_router(dream.router)  # CerebroCortex Dream Engine
router.include_router(memory_import.router)  # Universal Memory Import (The Transmuter)
router.include_router(sentinel.router)  # SensorHead Sentinel — autonomous surveillance
router.include_router(app_distribution.router)  # APK distribution — version info + download
router.include_router(agent_portability.router)  # Agent Portability — export/import entities
router.include_router(multiverse.router)  # Multiverse — cross-user portal system
router.include_router(athaverse.router)  # Athaverse VR — Quest 3 agent chat + tools
router.include_router(hermes_router, prefix="/hermes", tags=["Hermes Agent Bridge"])  # Hermes Agent Bridge
router.include_router(mcp_router, prefix="/mcp", tags=["MCP Server"])  # MCP Server
