import asyncio
import logging

import uvicorn

from app.app import create_app
from app.config import settings
from app.dependencies import set_node_instance
from app.grpc.server import run_grpc_server
from app.raft.node import RaftNode
from app.utils import logger as _  # noqa: F401 - Import to configure logging

logger = logging.getLogger(__name__)


async def main():
    node_id = settings.NODE_ID

    logger.info(f"Starting node {node_id}")
    logger.info(f"  HTTP port: {settings.HTTP_PORT}")
    logger.info(f"  gRPC port: {settings.GRPC_PORT}")
    logger.info(f"  Peers: {settings.PEERS}")

    # Initialize raft node
    peers = (
        settings.PEERS
        if isinstance(settings.PEERS, list)
        else [settings.PEERS]
        if settings.PEERS
        else []
    )
    raft_node = RaftNode(node_id=node_id, peers=peers)

    set_node_instance(raft_node)

    fastapi_app = create_app()

    http_config = uvicorn.Config(
        app=fastapi_app, host=settings.HOST, port=settings.HTTP_PORT, log_level="info"
    )

    http_server = uvicorn.Server(http_config)
    grpc_task = asyncio.create_task(run_grpc_server(raft_node))
    raft_task = asyncio.create_task(raft_node.start())

    try:
        await http_server.serve()
    finally:
        grpc_task.cancel()
        raft_task.cancel()
        try:
            await grpc_task
        except asyncio.CancelledError:
            pass
        try:
            await raft_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(main())
