import logging

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route, WebSocketRoute

from app.balancer.pool import ServerPool
from app.config import settings
from app.handlers.http import HTTPHandler
from app.handlers.websocket import WebSocketHandler

logger = logging.getLogger(__name__)

pool = ServerPool(settings.SERVERS)  # type: ignore[arg-type]
http_handler = HTTPHandler(pool)
ws_handler = WebSocketHandler(pool)


async def http_endpoint(request):
    return await http_handler.handle(request)


async def ws_endpoint(websocket):
    await ws_handler.handle(websocket)


routes = [
    Route(
        "/{path:path}",
        http_endpoint,
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    ),
    WebSocketRoute("/ws/{path:path}", ws_endpoint),
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
]

app = Starlette(
    routes=routes,
    middleware=middleware,
)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Serving servers: {settings.SERVERS}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down load balancer")
