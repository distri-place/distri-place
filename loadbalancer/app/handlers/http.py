import logging

import httpx
from starlette.requests import Request
from starlette.responses import Response

from app.balancer.pool import ServerPool

logger = logging.getLogger(__name__)


class HTTPHandler:
    def __init__(self, pool: ServerPool):
        self.pool = pool
        self.client = httpx.AsyncClient(timeout=30.0)

    async def handle(self, request: Request) -> Response:
        if not self.pool.servers:
            return Response("no servers", status_code=503)

        body = await request.body()
        headers = dict(request.headers)
        headers.pop("host", None)
        headers.pop("connection", None)

        # Try all servers
        for _ in range(len(self.pool.servers)):
            server = self.pool.get_next_server()

            url = f"{server.http_url}{request.url.path}"
            if request.url.query:
                url += f"?{request.url.query}"

            logger.debug(
                f"Proxying {request.method} {request.url.path} to {server.host}:{server.port}"
            )

            try:
                resp = await self.client.request(
                    method=request.method,
                    url=url,
                    headers=headers,
                    content=body,
                )

                return Response(
                    content=resp.content,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                )
            except httpx.RequestError as e:
                logger.warning(f"Failed to connect to {server.host}:{server.port}: {e}")
                continue

        return Response("all servers failed", status_code=502)
