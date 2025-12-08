import asyncio
import logging

from starlette.websockets import WebSocket, WebSocketDisconnect
import websockets

from app.balancer.pool import ServerPool

logger = logging.getLogger(__name__)


class WebSocketHandler:
    def __init__(self, pool: ServerPool):
        self.pool = pool

    async def handle(self, client_ws: WebSocket):
        await client_ws.accept()

        server = self.pool.get_next_server()
        if not server:
            await client_ws.close(code=1013, reason="no servers")
            return

        url = server.ws_url

        try:
            async with websockets.connect(url) as backend_ws:
                await asyncio.gather(
                    self._forward(client_ws, backend_ws, to_backend=True),
                    self._forward(client_ws, backend_ws, to_backend=False),
                )
        except (WebSocketDisconnect, websockets.ConnectionClosed):
            pass

    async def _forward(
        self, client_ws: WebSocket, backend_ws: websockets.ClientConnection, to_backend: bool
    ):
        try:
            if to_backend:
                async for msg in client_ws.iter_text():
                    await backend_ws.send(msg)
            else:
                async for msg in backend_ws:
                    await client_ws.send_text(msg)
        except:
            pass

