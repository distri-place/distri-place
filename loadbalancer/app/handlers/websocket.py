import asyncio
import logging

from starlette.websockets import WebSocket
import websockets

from app.balancer.pool import ServerPool

logger = logging.getLogger(__name__)


class WebSocketHandler:
    def __init__(self, pool: ServerPool):
        self.pool = pool

    async def handle(self, client_ws: WebSocket):
        await client_ws.accept()

        if not self.pool.servers:
            await client_ws.close(code=1013, reason="no servers")
            return

        # Try all servers
        for _ in range(len(self.pool.servers)):
            server = self.pool.get_next_server()
            url = server.ws_url

            logger.debug(f"Trying WebSocket connection to {server.host}:{server.port}")

            try:
                async with websockets.connect(url) as backend_ws:
                    await asyncio.gather(
                        self._forward(client_ws, backend_ws, to_backend=True),
                        self._forward(client_ws, backend_ws, to_backend=False),
                    )
                return
            except (websockets.ConnectionClosed, websockets.InvalidURI, OSError) as e:
                logger.warning(f"Failed to connect to WebSocket {server.host}:{server.port}: {e}")
                continue

        await client_ws.close(code=1013, reason="all servers failed")

    async def _forward(
        self, client_ws: WebSocket, backend_ws: websockets.ClientConnection, to_backend: bool
    ):
        try:
            if to_backend:
                async for msg in client_ws.iter_text():
                    await backend_ws.send(msg)
            else:
                async for backend_msg in backend_ws:
                    if isinstance(backend_msg, bytes):
                        await client_ws.send_bytes(backend_msg)
                    else:
                        await client_ws.send_text(backend_msg)
        except Exception:
            pass
