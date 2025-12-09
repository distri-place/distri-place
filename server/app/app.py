import asyncio
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.client.routes import router as client_router
from app.api.ws.routes import router as ws_router
from app.canvas.state import Canvas
from app.client.manager import ClientManager
from app.config import settings
from app.dependencies import (
    get_node_instance,
    set_canvas_instance,
    set_client_manager_instance,
    set_node_instance,
)
from app.grpc.server import run_grpc_server
from app.raft.node import RaftNode


def create_app() -> FastAPI:
    canvas = Canvas()
    raft_node = RaftNode(node_id=settings.NODE_ID, peers=settings.PEERS, canvas=canvas)
    client_manager = ClientManager()

    set_canvas_instance(canvas)
    set_node_instance(raft_node)
    set_client_manager_instance(client_manager)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        grpc_server = await run_grpc_server(raft_node)
        raft_task = asyncio.create_task(raft_node.start())

        def on_update(x: int, y: int, color: int) -> None:
            asyncio.create_task(
                client_manager.broadcast(
                    {"type": "pixel", "content": {"x": x, "y": y, "color": color}}
                )
            )

        canvas.on_update = on_update

        yield

        # Shutdown
        raft_task.cancel()
        await grpc_server.stop(grace=5)

    app = FastAPI(lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(client_router, prefix="/client")
    app.include_router(ws_router, prefix="/ws")

    @app.get("/")
    def home(node: RaftNode = Depends(get_node_instance)):
        return {
            "message": f"Hello from {node.node_id}!",
            "node_id": node.node_id,
            "status": "active",
        }

    return app


# Create the app instance for uvicorn
app = create_app()
