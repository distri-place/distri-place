import logging

from app.balancer.strategy import RoundRobinStrategy
from app.schemas import ServerNode

logger = logging.getLogger(__name__)


class ServerPool:
    def __init__(self, servers: list[ServerNode]):
        self.strategy = RoundRobinStrategy()
        self.servers = servers

    def get_next_server(self) -> ServerNode:
        return self.strategy.select(self.servers)
