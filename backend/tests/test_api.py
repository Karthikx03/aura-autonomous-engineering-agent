"""Tests for the FastAPI app (backend/app/main.py + backend/app/api/*).

`POST /api/tasks` exercises the full sibling-owned orchestrator stack
(llm/tools/agents/orchestrator); by the time this suite runs those modules
have landed and imported cleanly (see test_create_task_* below), but the
simple GET routes are asserted independently of that so this file stays
meaningful even if a sibling module regresses later.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.api import task_store
from app.main import app
from app.websocket.events import AgentEvent, EventType
from app.websocket.manager import ConnectionManager


class _FakeSocket:
    """Minimal stand-in for a FastAPI WebSocket: async send_text only."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[str] = []

    async def send_text(self, data: str) -> None:
        if self.fail:
            raise RuntimeError("socket closed")
        self.sent.append(data)


def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "AURA"}


def test_list_providers() -> None:
    client = TestClient(app)
    response = client.get("/api/providers")
    assert response.status_code == 200
    body = response.json()
    assert "mock" in body["available"]
    assert body["default"] == "mock"


def test_get_unknown_task_404() -> None:
    client = TestClient(app)
    response = client.get("/api/tasks/does-not-exist")
    assert response.status_code == 404


def test_get_unknown_task_events_404() -> None:
    client = TestClient(app)
    response = client.get("/api/tasks/does-not-exist/events")
    assert response.status_code == 404


def test_metrics_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "tool_calls_total" in response.json()


def test_create_task_returns_task_id_when_orchestrator_wiring_available(tmp_path) -> None:
    """POST /api/tasks should always respond immediately with a task_id,
    without waiting for the (background) orchestrator run to finish."""
    if main_module._ORCHESTRATOR_IMPORT_ERROR is not None:
        import pytest

        pytest.xfail(f"Orchestrator wiring not importable yet: {main_module._ORCHESTRATOR_IMPORT_ERROR}")

    client = TestClient(app)
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    response = client.post(
        "/api/tasks", json={"goal": "Add a hello world endpoint", "repo_path": str(repo_path), "provider": "mock"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "task_id" in body
    assert body["task_id"] in task_store.tasks

    lookup = client.get(f"/api/tasks/{body['task_id']}")
    assert lookup.status_code == 200
    assert lookup.json()["task_id"] == body["task_id"]


@pytest.mark.asyncio
async def test_connection_manager_broadcasts_to_scoped_socket() -> None:
    manager = ConnectionManager()
    socket = _FakeSocket()
    await manager.connect(socket, task_id="task-1")

    event = AgentEvent(type=EventType.TASK_STARTED, agent="orchestrator", message="go", task_id="task-1")
    await manager.broadcast(event)

    assert len(socket.sent) == 1
    assert "task-1" in socket.sent[0]


@pytest.mark.asyncio
async def test_connection_manager_does_not_leak_across_tasks() -> None:
    manager = ConnectionManager()
    socket = _FakeSocket()
    await manager.connect(socket, task_id="task-1")

    event = AgentEvent(type=EventType.TASK_STARTED, agent="orchestrator", message="go", task_id="task-2")
    await manager.broadcast(event)

    assert socket.sent == []


@pytest.mark.asyncio
async def test_connection_manager_disconnect_stops_delivery() -> None:
    manager = ConnectionManager()
    socket = _FakeSocket()
    await manager.connect(socket, task_id="task-1")
    manager.disconnect(socket, task_id="task-1")

    event = AgentEvent(type=EventType.TASK_STARTED, agent="orchestrator", message="go", task_id="task-1")
    await manager.broadcast(event)

    assert socket.sent == []


@pytest.mark.asyncio
async def test_connection_manager_drops_dead_sockets_on_broadcast() -> None:
    manager = ConnectionManager()
    good = _FakeSocket()
    bad = _FakeSocket(fail=True)
    await manager.connect(good, task_id="task-1")
    await manager.connect(bad, task_id="task-1")

    event = AgentEvent(type=EventType.TASK_STARTED, agent="orchestrator", message="go", task_id="task-1")
    await manager.broadcast(event)

    assert len(good.sent) == 1
    # The failing socket should have been dropped without raising.
    assert bad not in manager._connections.get("task-1", set())
