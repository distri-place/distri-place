import asyncio

from app.raft.consensus import RaftConsensus


class Node:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.raft = RaftConsensus(node_id)
        self.background_tasks = []

    async def start(self):
        print(f"Node {self.node_id} starting up...")

        # Initialize Raft consensus
        print(f"Node {self.node_id} initializing Raft consensus (state: {self.raft.state.value})")
        # TODO: Join cluster if peers exist
        # TODO: Start background heartbeat/election tasks

        print(f"Node {self.node_id} is now active")

    async def stop(self):
        print(f"Node {self.node_id} shutting down...")

        # Stop Raft consensus
        print(f"Node {self.node_id} stopping Raft consensus")

        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        print(f"Node {self.node_id} stopped")

    def get_status(self) -> str:
        return "ok"
