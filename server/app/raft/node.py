from __future__ import annotations

import asyncio
import base64
from collections import defaultdict
from enum import Enum
from io import BytesIO
import json
import random
from typing import cast

from PIL import Image
from typing_extensions import Buffer

from app.client.manager import manager as client_manager
from app.generated.grpc.messages_pb2 import AppendEntriesResponse, LogEntry
from app.grpc.client import RaftClient
from app.raft.log import RaftLog


class Role(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


def init_canvas_image(
    width: int = 64, height: int = 64, color: tuple[int, int, int] = (255, 255, 255)
) -> Image.Image:
    return Image.new("RGB", (width, height), color)


class RaftNode:
    def __init__(self, node_id: str, peers: list[str]):
        self.node_id = node_id
        self.role = Role.FOLLOWER
        self.current_term = 0
        self.voted_for: str | None = None
        self.leader_id: str | None = None
        self.commit_index = 0
        self.log = RaftLog()
        self.peers = peers
        self.peer_commit_index: dict[str, int] = defaultdict(int)
        self.canvas = init_canvas_image()

        # gRPC components - clean separation
        self.grpc_client = RaftClient(node_id)
        self.election_timeout_task: asyncio.Task | None = None
        self.heartbeat_task: asyncio.Task | None = None

    async def start(self):
        await self._start_election_timeout()
        await self._start_heartbeat()

    async def stop(self):
        if self.election_timeout_task:
            self.election_timeout_task.cancel()
        if self.heartbeat_task:
            self.heartbeat_task.cancel()

        await self.grpc_client.close_all()

    async def start_election(self):
        if self.is_leader():
            return
        self.role = Role.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.leader_id = None
        await self._reset_election_timeout()
        term = self.current_term
        majority = (len(self.peers) + 1) // 2 + 1

        lli, llt = self.log.get_last_log_index(), self.log.get_last_log_term()

        if self.current_term != term or self.role != Role.CANDIDATE:
            return

        results = await self.grpc_client.broadcast_request_votes(self.peers, term, lli, llt)

        results = [resp for resp in results if resp is not None]
        higher_terms = [resp for resp in results if resp.term > term]
        if higher_terms:
            resp = higher_terms[0]
            self.role = Role.FOLLOWER
            self.current_term = resp.term
            self.voted_for = None
            self.leader_id = None
            return
        votes = 1 + len([resp for resp in results if resp.vote_granted])
        if votes >= majority:
            self.role = Role.LEADER
            self.leader_id = self.node_id

    async def send_heartbeat_once(self):
        if not self.is_leader():
            return
        await self.grpc_client.broadcast_append_entries(
            self.peers,
            self.current_term,
            self.node_id,
            self.log.get_last_log_index(),
            self.log.get_last_log_term(),
            [],
            self.commit_index,
        )

    async def _start_election_timeout(self):
        if self.election_timeout_task:
            self.election_timeout_task.cancel()
        self.election_timeout_task = asyncio.create_task(self._election_timeout_loop())

    async def _start_heartbeat(self):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _reset_election_timeout(self):
        await self._start_election_timeout()

    async def _election_timeout_loop(self):
        while True:
            try:
                await asyncio.sleep(random.uniform(1.5, 3.0))
                await self.start_election()
            except asyncio.CancelledError:
                return

    async def _heartbeat_loop(self):
        while True:
            try:
                await asyncio.sleep(1.0)
                await self.send_heartbeat_once()
            except asyncio.CancelledError:
                return

    def is_leader(self) -> bool:
        return self.role == Role.LEADER

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
            self.current_term,
            self.leader_id or self.node_id,
            self.log.get_last_log_index(),
            self.log.get_last_log_term(),
            entries,
            self.commit_index,
        )
        if not resp.success:
            pass

    async def peer_health_check(self, node: str):
        return await self.grpc_client.health_check(node)

    async def set_pixel(self, x: int, y: int, color: str, user_id: str) -> bool:
        # Only leader can set pixels
        if self.is_leader():
            data = {"x": x, "y": y, "color": color, "user_id": user_id}
            entry = LogEntry(
                term=self.current_term,
                index=self.log.get_last_log_index() + 1,
                command="pixel",
                data=json.dumps(data).encode("utf-8"),
            )
            self.log.append(entry)

            threshold = (len(self.peers) + 1) // 2 + 1

            requests = []
            for peer in self.peers:
                prev_commit_index = self.peer_commit_index[peer]
                next_commit_index = prev_commit_index + 1
                prev_term = 0
                if prev_commit_index > 0:
                    prev_term = self.log[prev_commit_index].term
                requests.append(
                    self.grpc_client.append_entries(
                        peer,
                        self.current_term,
                        self.node_id,
                        prev_commit_index,
                        prev_term,
                        self.log.get_entries_after(next_commit_index),
                        self.commit_index,
                    )
                )

            responses = await asyncio.gather(*requests, return_exceptions=True)

            # map each response to its peer and filter out failed responses
            responses = zip(self.peers, responses)
            responses = [
                (peer, resp) for peer, resp in responses if isinstance(resp, AppendEntriesResponse)
            ]

            # update peer last commit indices
            for peer, resp in responses:
                self.peer_commit_index[peer] = resp.match_index

            # count self in successful commits
            success_count = 1 + sum(1 for _, resp in responses if resp.success)

            if success_count < threshold:
                return False

            # commit the entry if majority have replicated it
            self.commit_index = self.log.get_last_log_index()
            await self.apply_command(entry.command, data)
        else:  # Forward to leader
            if self.leader_id:
                await self.grpc_client.set_pixel(self.leader_id, x, y, color, user_id)
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
            except json.JSONDecodeError:
                return
        match command:
            case "pixel" if isinstance(data, dict):
                self.canvas.putpixel(
                    (data["x"], data["y"]),
                    tuple(int(data["color"][i : i + 2], 16) for i in (1, 3, 5)),
                )
                await client_manager.broadcast("pixel", data)
            case _:
                pass
