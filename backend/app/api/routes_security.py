"""GET /api/tasks/{id}/security -- the security scan report for a task, if any."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api import task_store
from app.orchestrator.state import SecurityReport

router = APIRouter(prefix="/api", tags=["security"])


@router.get("/tasks/{task_id}/security")
async def get_task_security(task_id: str) -> SecurityReport | None:
    state = task_store.tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    return state.security_report
