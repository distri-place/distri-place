import logging

import uvicorn

from app.app import create_app
from app.config import settings
from app.utils import logger as _  # noqa: F401 - Import to configure logging

logger = logging.getLogger(__name__)


def main():
    from app.utils.logger import LOGGING_CONFIG

    node_id = settings.NODE_ID

    logger.info(f"Starting node {node_id}")
    logger.info(f"  HTTP port: {settings.HTTP_PORT}")
    logger.info(f"  gRPC port: {settings.GRPC_PORT}")
    logger.info(f"  Peers: {settings.PEERS()}")

    app = create_app()

    uvicorn.run(app, host=settings.HOST, port=settings.HTTP_PORT, log_config=LOGGING_CONFIG)


if __name__ == "__main__":
    main()
