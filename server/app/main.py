import argparse
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.client.routes import router as client_router
from app.node.node import Node

# Global node instance
node_instance: Node | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    global node_instance

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


@app.get("/")
def home():
    """Health check endpoint."""
    global node_instance
    if node_instance:
        return {
            "message": f"Hello from {node_instance.node_id}!",
            "node_id": node_instance.node_id,
            "status": "active",
        }
    return {"message": "Hello from server!", "status": "initializing"}


def get_port_for_node(node_id: str) -> int:
    """Get the port number for a given node ID."""
    port_map = {"node-1": 8000, "node-2": 8001, "node-3": 8002}
    return port_map.get(node_id, 8000)


if __name__ == "__main__":
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--node-id",
        type=str,
        default="node-1",
        help="Node ID",
    )
    args = parser.parse_args()

    node_instance = Node(args.node_id)

    port = get_port_for_node(args.node_id)
    print(f"Initializing node: {args.node_id} on port {port}")

    uvicorn.run(app, host="0.0.0.0", port=port)
