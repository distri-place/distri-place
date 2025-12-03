import asyncio

import uvicorn

from app.app import create_app
from app.config import settings
from app.dependencies import set_node_instance
from app.grpc.server import run_grpc_server
from app.raft.node import RaftNode


async def main():
    # Use node_id from settings (which can be overridden via CLI)
    node_id = settings.NODE_ID

    print(f"Starting node {node_id}")
    print(f"  HTTP port: {settings.HTTP_PORT}")
    print(f"  gRPC port: {settings.GRPC_PORT}")
    print(f"  Peers: {settings.PEERS}")

    # Initialize raft node
    peers = (
        settings.PEERS
        if isinstance(settings.PEERS, list)
        else [settings.PEERS]
        if settings.PEERS
        else []
    )
    raft_node = RaftNode(node_id=node_id, peers=peers)

    # Set the node instance for the FastAPI app
    set_node_instance(raft_node)

    # Create FastAPI app
    fastapi_app = create_app()

    # Configure uvicorn
    http_config = uvicorn.Config(
        app=fastapi_app, host=settings.HOST, port=settings.HTTP_PORT, log_level="info"
    )
    http_server = uvicorn.Server(http_config)

    # Start all services concurrently
    try:
        await asyncio.gather(
            http_server.serve(),
            run_grpc_server(raft_node),
            raft_node.start(),
        )
    except (KeyboardInterrupt, asyncio.CancelledError):
        print(f"\nShutting down node {node_id}")
    finally:
        await raft_node.stop()


if __name__ == "__main__":
    asyncio.run(main())
