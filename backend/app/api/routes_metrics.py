"""GET /api/metrics -- process-local metrics snapshot (tool calls, LLM calls, ...)."""
from __future__ import annotations

from fastapi import APIRouter

from app.observability.logger import METRICS

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/metrics")
async def get_metrics() -> dict:
    return METRICS.snapshot()
