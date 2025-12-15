from abc import ABC, abstractmethod

from app.schemas import ServerNode


class LoadBalancingStrategy(ABC):
    @abstractmethod
    def select(self, servers: list[ServerNode]) -> ServerNode:
        pass


class RoundRobinStrategy(LoadBalancingStrategy):
    def __init__(self):
        self.current = 0

    def select(self, servers: list[ServerNode]) -> ServerNode:
        if not servers:
            raise ValueError("No servers available")

        # Ensure current index is within bounds
        self.current = self.current % len(servers)
        server = servers[self.current]
        self.current = (self.current + 1) % len(servers)
        return server
