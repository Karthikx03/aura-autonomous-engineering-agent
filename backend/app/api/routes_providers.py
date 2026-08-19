"""GET /api/providers -- which LLM providers are wired up and which is default."""
from __future__ import annotations

from fastapi import APIRouter

from app.config import get_settings
from app.llm.factory import available_providers

router = APIRouter(prefix="/api", tags=["providers"])


@router.get("/providers")
async def list_providers() -> dict:
    settings = get_settings()
    return {"available": available_providers(), "default": settings.default_llm_provider}
