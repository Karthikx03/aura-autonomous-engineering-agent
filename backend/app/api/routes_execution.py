"""GET /api/tasks/{id}/events -- the event history recorded for a task."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api import task_store
from app.websocket.events import AgentEvent

router = APIRouter(prefix="/api", tags=["execution"])


@router.get("/tasks/{task_id}/events")
async def get_task_events(task_id: str) -> list[AgentEvent]:
    if task_id not in task_store.tasks:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    return task_store.events.get(task_id, [])
