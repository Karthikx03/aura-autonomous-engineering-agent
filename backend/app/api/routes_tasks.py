"""POST /api/tasks -- kick off an autonomous task run; GET to look it up.

The heavy lifting (constructing the Orchestrator from llm/tools/agents,
which are sibling-owned modules that may not exist yet during development)
lives in ``app.main.build_orchestrator``. This module only depends on that
function being *importable*, not on the modules it wires together, and
imports it lazily inside the handler so a broken sibling import surfaces as
a clean HTTP error instead of an app-wide crash.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api import task_store
from app.orchestrator.state import TaskState

logger = logging.getLogger("aura.api.tasks")

router = APIRouter(prefix="/api", tags=["tasks"])

# backend/app/api/routes_tasks.py -> backend/app/api -> backend/app -> backend -> <project root>
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_repo_path(repo_path: str) -> str:
    """Anchor a possibly-relative ``repo_path`` to the project root.

    Every downstream consumer (the repo analyst, the sandboxed file tools,
    the test/command runners) does ``Path(repo_path).resolve()`` or
    equivalent, which resolves relative paths against the *server
    process's* current working directory -- not the repository root. That
    makes API behavior depend on the directory uvicorn happened to be
    launched from, so callers sending a natural relative path like
    ``"demo/broken_project"`` (exactly what the frontend's "Run Demo"
    button sends) would get a spurious "No such file or directory" if the
    server wasn't started from the project root. Resolving once, here, at
    the API boundary makes every other module's behavior independent of
    server cwd.
    """
    path = Path(repo_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path.resolve())


class CreateTaskRequest(BaseModel):
    goal: str
    repo_path: str
    provider: str | None = None


async def _run_and_track(task_id: str, goal: str, repo_path: str, provider: str | None) -> None:
    """Background coroutine: build the orchestrator, run the task, keep
    ``task_store.tasks[task_id]`` up to date, and best-effort persist the
    final result to the database."""
    try:
        from app.main import build_orchestrator
    except Exception as exc:  # noqa: BLE001
        logger.exception("Could not build orchestrator for task %s", task_id)
        current = task_store.tasks.get(task_id)
        if current is not None:
            current.status = current.status.__class__.FAILED
            current.error = f"Orchestrator unavailable: {exc}"
        return

    try:
        orchestrator = build_orchestrator(repo_path, provider=provider)
        final_state = await orchestrator.run_task(goal=goal, repo_path=repo_path, task_id=task_id)
        task_store.tasks[task_id] = final_state
    except Exception as exc:  # noqa: BLE001 - never let a background task raise unseen
        logger.exception("Task %s failed", task_id)
        current = task_store.tasks.get(task_id)
        if current is not None:
            current.status = current.status.__class__.FAILED
            current.error = str(exc)

    await _persist_best_effort(task_store.tasks.get(task_id))


async def _persist_best_effort(state: TaskState | None) -> None:
    if state is None:
        return
    try:
        from app.memory.db import get_sessionmaker
        from app.memory.models import Project, TaskRun

        sessionmaker = get_sessionmaker()
        async with sessionmaker() as session:
            project = Project(name=state.repo_path, repo_path=state.repo_path)
            session.add(project)
            await session.flush()
            task_run = TaskRun(
                project_id=project.id,
                goal=state.goal,
                status=state.status.value if hasattr(state.status, "value") else str(state.status),
                iterations=state.iteration,
                tests_passed=state.final_test_report.passed if state.final_test_report else 0,
                tests_failed=state.final_test_report.failed if state.final_test_report else 0,
                success=state.succeeded,
            )
            session.add(task_run)
            await session.commit()
    except Exception:  # noqa: BLE001 - persistence is best-effort, never fails the request
        logger.exception("Best-effort persistence of task %s failed", state.task_id)


@router.post("/tasks")
async def create_task(request: CreateTaskRequest) -> dict:
    repo_path = _resolve_repo_path(request.repo_path)
    if not Path(repo_path).is_dir():
        raise HTTPException(status_code=400, detail=f"repo_path does not exist: {repo_path}")
    state = TaskState(goal=request.goal, repo_path=repo_path)
    task_store.tasks[state.task_id] = state
    task_store.events.setdefault(state.task_id, [])
    asyncio.create_task(_run_and_track(state.task_id, request.goal, repo_path, request.provider))
    return {"task_id": state.task_id}


@router.get("/tasks")
async def list_tasks() -> list[TaskState]:
    return list(task_store.tasks.values())


@router.get("/tasks/{task_id}")
async def get_task(task_id: str) -> TaskState:
    state = task_store.tasks.get(task_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"Unknown task_id: {task_id}")
    return state
