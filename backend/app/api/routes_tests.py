"""GET /api/tasks/{id}/tests -- the final test report for a task, if any."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api import task_store
from app.orchestrator.state import TestReport

router = APIRouter(prefix="/api", tags=["tests"])


@router.get("/tasks/{task_id}/tests")
async def get_task_tests(task_id: str) -> TestReport | None:
    state = task_store.tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    return state.final_test_report
