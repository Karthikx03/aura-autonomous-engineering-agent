"""AURA FastAPI application entrypoint."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    routes_execution,
    routes_metrics,
    routes_providers,
    routes_security,
    routes_tasks,
    routes_tests,
    routes_ws,
)
from app.api.task_store import record_event
from app.config import get_settings
from app.memory.db import init_db
from app.websocket.events import AgentEvent
from app.websocket.manager import manager

logger = logging.getLogger("aura.main")

# ---------------------------------------------------------------------------
# Cross-module wiring for the Orchestrator.
#
# llm/tools/agents/orchestrator are owned by sibling engineers and may not
# exist yet (or may be mid-refactor) while this module is developed/tested.
# Importing them at module scope, but inside a try/except, means:
#   (a) `python -m py_compile app/main.py` and a bare `import app.main`
#       never fail just because a sibling module is missing/broken, and
#   (b) once those modules exist, `build_orchestrator` below picks them up
#       automatically with zero changes here.
# Any failure is captured in `_ORCHESTRATOR_IMPORT_ERROR` and surfaced as a
# clean error from the `/api/tasks` handler rather than crashing the app.
# ---------------------------------------------------------------------------
_ORCHESTRATOR_IMPORT_ERROR: str | None = None
try:
    from app.agents.coder import CoderAgent
    from app.agents.debugger import DebuggerAgent
    from app.agents.planner import PlannerAgent
    from app.agents.repo_analyst import RepoAnalystAgent
    from app.agents.security import SecurityAgent
    from app.agents.tester import TestingAgent
    from app.git_integration.git_manager import GitManager
    from app.llm.factory import get_provider
    from app.orchestrator.orchestrator import Orchestrator
    from app.tools.registry import build_default_registry
except Exception as exc:  # noqa: BLE001 - any import failure just disables task creation
    _ORCHESTRATOR_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
    logger.warning("Orchestrator wiring unavailable at import time: %s", _ORCHESTRATOR_IMPORT_ERROR)


_orchestrator_cache: dict[str, Any] = {}


def build_orchestrator(repo_root: str, provider: str | None = None) -> Any:
    """Construct (and cache, per repo_root+provider) a fully wired Orchestrator.

    Raises RuntimeError when the sibling agent/llm/tools/orchestrator
    modules this depends on are not importable -- the ``/api/tasks`` POST
    handler catches that and turns it into a clean error response instead
    of a 500 traceback or an app-wide crash.
    """
    if _ORCHESTRATOR_IMPORT_ERROR is not None:
        raise RuntimeError(f"Orchestrator not available: {_ORCHESTRATOR_IMPORT_ERROR}")

    cache_key = f"{repo_root}:{provider or ''}"
    cached = _orchestrator_cache.get(cache_key)
    if cached is not None:
        return cached

    settings = get_settings()
    llm = get_provider(provider, settings)
    tools = build_default_registry(repo_root)

    async def event_sink(event: AgentEvent) -> None:
        record_event(event)
        await manager.broadcast(event)

    def git_committer(repo_path: str, message: str) -> str:
        return GitManager(repo_path).commit(message)

    orchestrator = Orchestrator(
        planner=PlannerAgent(llm, tools),
        repo_analyst=RepoAnalystAgent(llm, tools),
        coder=CoderAgent(llm, tools),
        tester=TestingAgent(llm, tools),
        debugger=DebuggerAgent(llm, tools),
        security=SecurityAgent(llm, tools),
        event_sink=event_sink,
        git_committer=git_committer,
    )
    _orchestrator_cache[cache_key] = orchestrator
    return orchestrator


app = FastAPI(title="AURA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for _router in (
    routes_providers.router,
    routes_tasks.router,
    routes_execution.router,
    routes_tests.router,
    routes_security.router,
    routes_metrics.router,
    routes_ws.router,
):
    app.include_router(_router)


@app.get("/")
async def health() -> dict:
    return {"status": "ok", "service": "AURA"}


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
