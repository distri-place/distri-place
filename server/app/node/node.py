from __future__ import annotations

import asyncio
import base64
import json
import random
from io import BytesIO
from typing import Any, cast, Coroutine

import grpc.aio as grpc
from PIL import Image
from typing_extensions import Buffer

from app.client.manager import manager as client_manager
from app.generated.grpc.messages_pb2 import (
    AppendEntriesRequest,
    RequestVoteRequest,
    AppendEntriesResponse,
    RequestVoteResponse,
    HealthCheckRequest,
    HealthCheckResponse,
    SetPixelRequest,
    SetPixelResponse,
    LogEntry,
)
from app.generated.grpc.messages_pb2_grpc import (
    RaftNodeServicer,
    add_RaftNodeServicer_to_server,
    RaftNodeStub
)
from app.raft.consensus import RaftConsensus
from app.utils.timers import AsyncTicker


def init_canvas_image(width: int = 64, height: int = 64, color: tuple[int, int, int] = (255, 255, 255)) -> Image.Image:
    return Image.new("RGB", (width, height), color)


def log_error(message: str):
    print(f"\x1b[38;5;{1}m", end="", flush=True)
    print(f"[ERROR] {message}", end="", flush=True)
    print("\x1b[0m", flush=True)


class Node(RaftNodeServicer):
    def __init__(self, node_id: str, peers: list[str]):
        self.node_id = node_id
        self.raft = RaftConsensus(node_id)
        self.background_tasks = set()
        self.peers = peers
        self._channels: dict[str, grpc.Channel | None] = {}
        self._stubs: dict[str, RaftNodeStub | None] = {}
        self.clients = []
        self.canvas = init_canvas_image()
        self.grpc_server: grpc.Server | None = None
        self.election_timeout = AsyncTicker(random.uniform(1.5, 3.0), self.start_election, start=False)
        self.heartbeat = AsyncTicker(1.0, self.send_heartbeat_once, start=False)

    def stub(self, node_id: str) -> RaftNodeStub:
        if not self._stubs.get(node_id, None):
            if not self._channels.get(node_id, None):
                self._channels[node_id] = grpc.insecure_channel(f"{node_id}:50051")
            self._stubs[node_id] = RaftNodeStub(self._channels[node_id])
        return self._stubs[node_id]

    async def peer_request_vote(self, node: str, term: int, last_log_index: int,
                                last_log_term: int) -> RequestVoteResponse | None:
        try:
            with grpc.insecure_channel(f"{node}:50051") as channel:
                return RaftNodeStub(channel).RequestVote(RequestVoteRequest(
                    term=term,
                    candidate_id=self.node_id,
                    last_log_index=last_log_index,
                    last_log_term=last_log_term,
                ))
        except Exception as e:
            return None

    async def start_election(self):
        if self.is_leader(): return
        self.raft.become_candidate()
        await self.election_timeout.reset()
        term = self.raft.current_term
        majority = (len(self.peers) + 1) // 2 + 1

        print(f"{self.node_id} requesting votes from peers...")

        lli, llt = self.last_log_index(), self.last_log_term()

        if self.raft.current_term != term or self.raft.state_name != "candidate":
            return

        requests: list[Coroutine[Any, Any, RequestVoteResponse]] = [
            self.peer_request_vote(peer, term, lli, llt)
            for peer in self.peers
        ]
        results: list[RequestVoteResponse] = await asyncio.gather(*requests, return_exceptions=True)

        results = [resp for resp in results if resp is not None]
        higher_terms = [resp for resp in results if resp.term > term]
        if higher_terms:
            resp = higher_terms[0]
            print(f"[{self.node_id}] Stepping down from candidate due to higher term {resp.term}")
            self.raft.become_follower(resp.term, leader=None)
            return
        votes = 1 + len([resp for resp in results if resp.vote_granted])
        if votes >= majority:
            print(f"[{self.node_id}] Elected leader for term {self.raft.current_term} with {votes} votes")
            self.raft.become_leader()

    async def send_heartbeat_once(self):
        if not self.is_leader():
            return
        for peer in self.peers:
            await self.stub(peer).AppendEntries(AppendEntriesRequest(
                term=self.raft.current_term,
                leader_id=self.node_id,
                prev_log_index=self.last_log_index(),
                prev_log_term=self.last_log_term(),
                leader_commit=self.raft.commit_index,
            ))

    async def start(self):
        print(f"Node {self.node_id} starting up...")
        print(f"Node {self.node_id} starting grpc server")
        self.grpc_server = grpc.server()
        add_RaftNodeServicer_to_server(self, self.grpc_server)
        self.grpc_server.add_insecure_port(f"{self.node_id}:50051")
        await self.grpc_server.start()
        print(f"Node {self.node_id} gRPC server started on {self.node_id}:50051")
        await self.peers_health_check()

        # Initialize Raft consensus
        print(f"Node {self.node_id} initializing Raft consensus (state: {self.raft.state_name})")
        # TODO: Join cluster if peers exist
        await self.start_election()
        self.election_timeout.start()
        self.heartbeat.start()
        print(f"Node {self.node_id} is now active")

    async def stop(self):
        print(f"Node {self.node_id} shutting down...")

        await self.election_timeout.stop()
        await self.heartbeat.stop()

        for channel in [ch for ch in self._channels.values() if ch]:
            await channel.close()

        # Stop Raft consensus
        print(f"Node {self.node_id} stopping Raft consensus")
        if self.grpc_server:
            print(f"Node {self.node_id} stopping gRPC server")
            await self.grpc_server.stop(0)
            await self.grpc_server.wait_for_termination(timeout=0.2)

        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        print(f"Node {self.node_id} stopped")

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
        print(f"{self.node_id} -> {node}.AppendEntries(...)")
        resp: AppendEntriesResponse = await self.stub(node).AppendEntries(AppendEntriesRequest(
            term=self.raft.current_term,
            leader_id=self.raft.leader_id,
            prev_log_index=self.last_log_index(),
            prev_log_term=self.last_log_term(),
            entries=entries,
            leader_commit=self.raft.commit_index,
        ))
        if not resp.success:
            print(f"AppendEntries to {node} failed: term={resp.term}, match_index={resp.match_index}")

    async def peer_health_check(self, node: str) -> HealthCheckResponse:
        print(f"{self.node_id} -> {node}.HealthCheck(...)")
        return await self.stub(node).HealthCheck(HealthCheckRequest(node_id=self.node_id))

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
                data=json.dumps(data).encode('utf-8')
            )
            req = AppendEntriesRequest(
                term=self.raft.current_term,
                leader_id=self.raft.leader_id,
                prev_log_index=self.last_log_index(),
                prev_log_term=self.last_log_term(),
                entries=[entry],
                leader_commit=self.raft.commit_index,
            )
            self.raft.log.append(entry)
            await asyncio.gather(*[self.stub(peer).AppendEntries(req) for peer in self.peers], return_exceptions=True)
            # TODO: check responses for majority and commit only if majority succeeded
            self.raft.commit_index = self.last_log_index()
            await self.apply_command(entry.command, data)
        else:  # Forward to leader
            async with grpc.insecure_channel(f"{self.raft.leader_id}:50051") as channel:
                req = SetPixelRequest(x=x, y=y, color=color, user_id=user_id)
                await RaftNodeStub(channel).SetPixel(req)
        return True

    async def peers_health_check(self, attempts: int = 3, delay: float = 1.0):
        for peer in self.peers:
            for i in range(attempts):
                try:
                    await self.stub(peer).HealthCheck(HealthCheckRequest(node_id=self.node_id))
                except Exception:
                    await asyncio.sleep(delay)

    async def RequestVote(self, request: RequestVoteRequest, context) -> RequestVoteResponse:
        await self.election_timeout.reset()
        if request.term > self.raft.current_term:
            self.raft.become_follower(request.term, leader=None)

        lli = self.last_log_index()
        llt = self.last_log_term()

        vote_granted = False
        up_to_date = (request.last_log_term > llt or (request.last_log_term == llt and request.last_log_index >= lli))

        if request.term == self.raft.current_term and up_to_date and (
                self.raft.voted_for in (None, request.candidate_id)):
            self.raft.voted_for = request.candidate_id
            vote_granted = True
            self.raft.leader_id = None

        return RequestVoteResponse(
            term=self.raft.current_term,
            vote_granted=vote_granted
        )

    async def apply_command(self, command: str, data: bytes | dict):
        if isinstance(data, bytes):
            try:
                data = json.loads(data.decode('utf-8'))
            except json.JSONDecodeError as e:
                log_error(f"Node {self.node_id}: failed to decode command data: {e}")
                data = None
        match command:
            case "pixel" if isinstance(data, dict):
                self.canvas.putpixel((data["x"], data["y"]), tuple(int(data["color"][i:i + 2], 16) for i in (1, 3, 5)))
                await client_manager.broadcast("pixel", data)
            case _:
                print(f"Node {self.node_id} received unknown command: {command}")

    async def SetPixel(self, request: SetPixelRequest, context) -> SetPixelResponse:
        assert self.raft.leader_id == self.node_id, "SetPixel can only be called on the leader"
        await self.set_pixel(request.x, request.y, request.color, request.user_id)
        return SetPixelResponse(status="ok")

    async def AppendEntries(self, request: AppendEntriesRequest, context) -> AppendEntriesResponse:
        if request.term < self.raft.current_term:
            # Reject request if term is outdated
            return AppendEntriesResponse(term=self.raft.current_term, success=False, match_index=-1)

        # Reset election timeout
        await self.election_timeout.reset()

        if request.term > self.raft.current_term or self.raft.state_name != "follower":
            self.raft.become_follower(request.term, leader=request.leader_id)
        else:
            self.raft.leader_id = request.leader_id

        if request.prev_log_index > self.last_log_index():
            # Prev log index is beyond current log
            return AppendEntriesResponse(
                term=self.raft.current_term,
                success=False,
                match_index=self.last_log_index(),
            )

        def get_term_at(idx: int) -> int:
            if idx == 0: return 0
            if 1 <= idx <= self.last_log_index(): return self.raft.log[idx - 1].term
            return -1

        if request.prev_log_index > 0:
            if get_term_at(request.prev_log_index) != request.prev_log_term:
                self.raft.log = self.raft.log[:request.prev_log_index - 1]
                return AppendEntriesResponse(
                    term=self.raft.current_term,
                    success=False,
                    match_index=self.last_log_index(),
                )

        for entry in request.entries:
            if entry.index <= self.last_log_index():
                if get_term_at(entry.index) != entry.term:
                    self.raft.log = self.raft.log[:entry.index - 1]
                    self.raft.log.append(entry)
                    await self.apply_command(entry.command, entry.data)
            else:
                self.raft.log.append(entry)
                await self.apply_command(entry.command, entry.data)

        if request.leader_commit > self.raft.commit_index:
            self.raft.commit_index = min(request.leader_commit, self.last_log_index())

        return AppendEntriesResponse(
            term=self.raft.current_term,
            success=True,
            match_index=self.last_log_index(),
        )

    async def HealthCheck(self, request: HealthCheckRequest, context) -> HealthCheckResponse:
        return HealthCheckResponse(
            node_id=self.node_id,
            status=await self.get_status()

        )


_instance: Node | None = None


def get_node_instance() -> Node:
    global _instance
    if _instance is None:
        from app.config import settings
        _instance = Node(node_id=settings.NODE_ID, peers=settings.PEERS)
    return _instance
