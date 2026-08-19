"""Process-local task/event bookkeeping shared by the task, execution, tests,
and security routers.

This is intentionally simple (plain dicts, no locking) -- AURA runs as a
single FastAPI process per deployment and asyncio gives us cooperative
scheduling, so plain dict mutation from route handlers/background tasks is
safe. Durable history lives in the SQL memory store (app.memory); this is
just the live view the API/dashboard reads while a task is running or
shortly after.
"""
from __future__ import annotations

from app.orchestrator.state import TaskState
from app.websocket.events import AgentEvent

# task_id -> latest TaskState snapshot
tasks: dict[str, TaskState] = {}

# task_id -> ordered list of every AgentEvent emitted for that task
events: dict[str, list[AgentEvent]] = {}


def record_event(event: AgentEvent) -> None:
    if event.task_id is None:
        return
    events.setdefault(event.task_id, []).append(event)


def reset() -> None:
    """Test helper: clear all in-memory state."""
    tasks.clear()
    events.clear()
