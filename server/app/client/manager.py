import asyncio
import json
from typing import Any
from uuid import uuid4

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._background_tasks: set[asyncio.Task] = set()
        self._clients: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        client_id = str(uuid4())
        async with self._lock:
            self._clients[client_id] = websocket
        return client_id

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            ws = self._clients.pop(client_id, None)
        if ws is not None:
            try:
                await ws.close()
            except Exception:
                pass

    async def broadcast(self, type: str, content: Any) -> None:
        async with self._lock:
            clients = list(self._clients.values())
        message = json.dumps({"type": type, "content": content})
        tasks = [asyncio.create_task(self._safe_send(ws, message)) for ws in clients]
        for task in tasks:
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def _safe_send(self, ws: WebSocket, data):
        try:
            await ws.send_text(data)
        except Exception:
            # optional: mark for cleanup, log, etc.
            pass


# This is the singleton used across the app
manager = ConnectionManager()
