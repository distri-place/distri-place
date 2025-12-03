from __future__ import annotations

import asyncio
import base64
from io import BytesIO
import json
import random
from typing import Any, cast

import grpc.aio as grpc
from PIL import Image
from typing_extensions import Buffer

from app.client.manager import manager as client_manager
from app.generated.grpc.messages_pb2 import LogEntry
from app.grpc.client import RaftClient
from app.grpc.server import create_grpc_server
from app.raft.consensus import RaftConsensus
from app.utils.timers import AsyncTicker


def make_entry(term: int, index: int, command: str, data: Any) -> LogEntry:
    return LogEntry(term=term, index=index, command=command, data=json.dumps(data).encode("utf-8"))


def init_canvas_image(
    width: int = 64, height: int = 64, color: tuple[int, int, int] = (255, 255, 255)
) -> Image.Image:
    return Image.new("RGB", (width, height), color)




class RaftNode:
    def __init__(self, node_id: str, peers: list[str]):
        self.node_id = node_id
        self.raft = RaftConsensus(node_id)
        self.peers = peers
        self.clients: list[Any] = []
        self.canvas = init_canvas_image()

        # gRPC components - clean separation
        self.grpc_client = RaftClient(node_id)
        self.grpc_server: grpc.Server | None = None
        self.election_timeout = AsyncTicker(
            random.uniform(1.5, 3.0), self.start_election, start=False
        )
        self.heartbeat = AsyncTicker(1.0, self.send_heartbeat_once, start=False)

    async def start(self):
        self.election_timeout.start()
        self.heartbeat.start()

    async def stop(self):
        await self.election_timeout.stop()
        await self.heartbeat.stop()

        # Close gRPC connections
        await self.grpc_client.close_all()
        if self.grpc_server:
            await self.grpc_server.stop(0.2)
            await self.grpc_server.wait_for_termination(timeout=0.2)

        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

    async def start_election(self):
        if self.is_leader():
            return
        self.raft.become_candidate()
        await self.election_timeout.reset()
        term = self.raft.current_term
        majority = (len(self.peers) + 1) // 2 + 1


        lli, llt = self.last_log_index(), self.last_log_term()

        if self.raft.current_term != term or self.raft.state_name != "candidate":
            return

        results = await self.grpc_client.broadcast_request_votes(self.peers, term, lli, llt)

        results = [resp for resp in results if resp is not None]
        higher_terms = [resp for resp in results if resp.term > term]
        if higher_terms:
            resp = higher_terms[0]
            self.raft.become_follower(resp.term, leader=None)
            return
        votes = 1 + len([resp for resp in results if resp.vote_granted])
        if votes >= majority:
            self.raft.become_leader()

    async def send_heartbeat_once(self):
        if not self.is_leader():
            return
        await self.grpc_client.broadcast_append_entries(
            self.peers,
            self.raft.current_term,
            self.node_id,
            self.last_log_index(),
            self.last_log_term(),
            [],
            self.raft.commit_index,
        )



    def is_leader(self) -> bool:
        return self.node_id == self.raft.leader_id

    async def get_status(self) -> str:
        return "ok"

    def encode_image_to_base64_png(self) -> str:
        buf = BytesIO()
        self.canvas.save(buf, format="PNG")
        png_bytes = cast(Buffer, buf.getvalue())
        return base64.b64encode(png_bytes).decode("ascii")

    async def node_append_entries(self, node: str, entries: list[LogEntry]) -> None:
        resp = await self.grpc_client.append_entries(
            node,
            self.raft.current_term,
            self.raft.leader_id or self.node_id,
            self.last_log_index(),
            self.last_log_term(),
            entries,
            self.raft.commit_index,
        )
        if not resp.success:

    async def peer_health_check(self, node: str):
        return await self.grpc_client.health_check(node)

    def last_log_index(self):
        return len(self.raft.log)

    def last_log_term(self):
        return 0 if len(self.raft.log) == 0 else self.raft.log[-1].term

    async def set_pixel(self, x: int, y: int, color: str, user_id: str) -> bool:
        # Only leader can set pixels
        if self.is_leader():
            data = {"x": x, "y": y, "color": color, "user_id": user_id}
            entry = LogEntry(
                term=self.raft.current_term,
                index=self.last_log_index() + 1,
                command="pixel",
                data=json.dumps(data).encode("utf-8"),
            )
            self.raft.log.append(entry)
            await self.grpc_client.broadcast_append_entries(
                self.peers,
                self.raft.current_term,
                self.raft.leader_id or self.node_id,
                self.last_log_index(),
                self.last_log_term(),
                [entry],
                self.raft.commit_index,
            )
            # TODO: check responses for majority and commit only if majority succeeded
            self.raft.commit_index = self.last_log_index()
            await self.apply_command(entry.command, data)
        else:  # Forward to leader
            if self.raft.leader_id:
                await self.grpc_client.set_pixel(self.raft.leader_id, x, y, color, user_id)
        return True

    async def peers_health_check(self, attempts: int = 3, delay: float = 1.0):
        for peer in self.peers:
            for _ in range(attempts):
                try:
                    await self.grpc_client.health_check(peer)
                except Exception:
                    await asyncio.sleep(delay)

    async def apply_command(self, command: str, data: bytes | dict):
        if isinstance(data, bytes):
            try:
                data = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError as e:
                data = None
        match command:
            case "pixel" if isinstance(data, dict):
                self.canvas.putpixel(
                    (data["x"], data["y"]),
                    tuple(int(data["color"][i : i + 2], 16) for i in (1, 3, 5)),
                )
                await client_manager.broadcast("pixel", data)
            case _:


_instance: RaftNode | None = None


def get_node_instance() -> RaftNode:
    global _instance
    if _instance is None:
        from app.config import settings

        _instance = RaftNode(node_id=settings.NODE_ID, peers=settings.PEERS)
    return _instance
