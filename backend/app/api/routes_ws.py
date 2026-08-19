"""WS /ws/tasks/{task_id} -- live AgentEvent stream for a single task."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/tasks/{task_id}")
async def task_events_ws(websocket: WebSocket, task_id: str) -> None:
    await manager.connect(websocket, task_id=task_id)
    try:
        while True:
            # We don't expect meaningful client->server traffic on this
            # stream; receiving just lets us detect disconnects promptly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, task_id=task_id)
