"""Tracks live WebSocket connections and fans out AgentEvents to them.

Kept independent of any particular route so it can be unit tested with
lightweight fake sockets (anything with an async ``send_text``) rather than
a running FastAPI/uvicorn server.
"""
from __future__ import annotations

import logging
from typing import Any, Protocol

from app.websocket.events import AgentEvent

logger = logging.getLogger("aura.websocket")


class _SendsText(Protocol):
    async def send_text(self, data: str) -> Any: ...


class ConnectionManager:
    """Bookkeeping for connected WebSocket clients, grouped by task_id."""

    def __init__(self) -> None:
        # task_id -> set of sockets subscribed to that task's events.
        # None is used as the key for connections not scoped to a task
        # (e.g. a global event stream), and broadcast() also fans out to it.
        self._connections: dict[str | None, set[Any]] = {}

    async def connect(self, websocket: Any, task_id: str | None = None) -> None:
        """Accept the handshake (if the socket exposes ``accept()``) and
        register it. ``task_id`` optionally scopes the socket to only
        receive events for that task; omit it for a global subscriber."""
        accept = getattr(websocket, "accept", None)
        if callable(accept):
            await accept()
        self._connections.setdefault(task_id, set()).add(websocket)

    def disconnect(self, websocket: Any, task_id: str | None = None) -> None:
        if task_id is not None:
            self._connections.get(task_id, set()).discard(websocket)
            return
        # Unscoped disconnect: remove this socket from every group.
        for sockets in self._connections.values():
            sockets.discard(websocket)

    async def broadcast(self, event: AgentEvent) -> None:
        """Send ``event`` to every socket subscribed to its task (plus any
        globally-subscribed sockets). Sockets that raise on send are treated
        as dead and silently dropped."""
        payload = event.model_dump_json()
        targets: set[Any] = set()
        targets |= self._connections.get(event.task_id, set())
        if event.task_id is not None:
            targets |= self._connections.get(None, set())

        dead: list[Any] = []
        for websocket in targets:
            try:
                await websocket.send_text(payload)
            except Exception:  # noqa: BLE001 - any send failure means the socket is dead
                dead.append(websocket)

        for websocket in dead:
            self.disconnect(websocket)


manager = ConnectionManager()
