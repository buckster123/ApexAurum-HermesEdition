"""
Hermes Agent Bridge

Allows Hermes AI agent to call ApexAurum tools via a simple HTTP API.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/hermes", tags=["Hermes Bridge"])
