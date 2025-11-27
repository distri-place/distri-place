from contextlib import asynccontextmanager
import dataclasses

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.client.routes import router as client_router
from app.api.ws.routes import router as ws_router
import app.node


@dataclasses.dataclass
class SetPixelArg:
    x: int
    y: int
    value: str


node_instance = app.node.get_node_instance()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""

    print(f"Starting node: {node_instance.node_id}")
    await node_instance.start()
    yield
    print(f"Stopping node: {node_instance.node_id}")
    await node_instance.stop()


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
def home():
    """Health check endpoint."""
    return {
        "message": f"Hello from {node_instance.node_id}!",
        "node_id": node_instance.node_id,
        "status": "active",
    }
