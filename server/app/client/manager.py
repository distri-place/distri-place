import asyncio
from typing import Any
from uuid import uuid4

from fastapi import WebSocket


class ClientManager:
    def __init__(self) -> None:
        self._clients: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self._tasks: set[asyncio.Task[Any]] = set()

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        client_id = str(uuid4())
        async with self._lock:
            self._clients[client_id] = ws
        return client_id

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            ws = self._clients.pop(client_id, None)
        if ws is not None:
            try:
                await ws.close()
            except Exception:
                pass

    async def broadcast(self, message: dict) -> None:
        async with self._lock:
            clients = list(self._clients.values())
        tasks = [asyncio.create_task(self._safe_send(ws, message)) for ws in clients]
        for task in tasks:
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _safe_send(self, ws: WebSocket, data):
        try:
            await ws.send_json(data)
        except Exception:
            pass
