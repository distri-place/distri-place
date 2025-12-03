import asyncio
from collections.abc import Coroutine
from typing import Any

import grpc.aio as grpc

from app.generated.grpc.messages_pb2 import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    HealthCheckRequest,
    HealthCheckResponse,
    LogEntry,
    RequestVoteRequest,
    RequestVoteResponse,
    SetPixelRequest,
    SetPixelResponse,
)
from app.generated.grpc.messages_pb2_grpc import RaftNodeStub


class RaftClient:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._channels: dict[str, grpc.Channel] = {}
        self._stubs: dict[str, RaftNodeStub] = {}

    def _get_stub(self, peer_id: str) -> RaftNodeStub:
        """Get or create a gRPC stub for the given peer"""
        if peer_id not in self._stubs:
            if peer_id not in self._channels:
                self._channels[peer_id] = grpc.insecure_channel(f"{peer_id}:50051")
            self._stubs[peer_id] = RaftNodeStub(self._channels[peer_id])
        return self._stubs[peer_id]

    async def request_vote(
        self, peer_id: str, term: int, last_log_index: int, last_log_term: int
    ) -> RequestVoteResponse:
        stub = self._get_stub(peer_id)
        request = RequestVoteRequest(
            term=term,
            candidate_id=self.node_id,
            last_log_index=last_log_index,
            last_log_term=last_log_term,
        )
        return await stub.RequestVote(request)

    async def append_entries(
        self,
        peer_id: str,
        term: int,
        leader_id: str,
        prev_log_index: int,
        prev_log_term: int,
        entries: list[LogEntry],
        leader_commit: int,
    ) -> AppendEntriesResponse:
        stub = self._get_stub(peer_id)
        request = AppendEntriesRequest(
            term=term,
            leader_id=leader_id,
            prev_log_index=prev_log_index,
            prev_log_term=prev_log_term,
            entries=entries,
            leader_commit=leader_commit,
        )
        return await stub.AppendEntries(request)

    async def health_check(self, peer_id: str) -> HealthCheckResponse:
        stub = self._get_stub(peer_id)
        request = HealthCheckRequest(node_id=self.node_id)
        return await stub.HealthCheck(request)

    async def set_pixel(
        self, peer_id: str, x: int, y: int, color: str, user_id: str
    ) -> SetPixelResponse:
        stub = self._get_stub(peer_id)
        request = SetPixelRequest(x=x, y=y, color=color, user_id=user_id)
        return await stub.SetPixel(request)

    async def broadcast_request_votes(
        self, peers: list[str], term: int, last_log_index: int, last_log_term: int
    ) -> list[RequestVoteResponse]:
        requests: list[Coroutine[Any, Any, RequestVoteResponse]] = [
            self.request_vote(peer, term, last_log_index, last_log_term) for peer in peers
        ]
        results: list[RequestVoteResponse | Exception] = await asyncio.gather(
            *requests, return_exceptions=True
        )
        return [resp for resp in results if isinstance(resp, RequestVoteResponse)]

    async def broadcast_append_entries(
        self,
        peers: list[str],
        term: int,
        leader_id: str,
        prev_log_index: int,
        prev_log_term: int,
        entries: list[LogEntry],
        leader_commit: int,
    ) -> list[AppendEntriesResponse]:
        requests = [
            self.append_entries(
                peer, term, leader_id, prev_log_index, prev_log_term, entries, leader_commit
            )
            for peer in peers
        ]
        results = await asyncio.gather(*requests, return_exceptions=True)
        return [resp for resp in results if isinstance(resp, AppendEntriesResponse)]

    async def broadcast_health_checks(self, peers: list[str]) -> list[HealthCheckResponse]:
        requests = [self.health_check(peer) for peer in peers]
        results = await asyncio.gather(*requests, return_exceptions=True)
        return [resp for resp in results if isinstance(resp, HealthCheckResponse)]

    async def close_all(self):
        for channel in self._channels.values():
            await channel.close()
        self._channels.clear()
        self._stubs.clear()

    async def peer_request_vote(
        self, peer_id: str, term: int, last_log_index: int, last_log_term: int
    ) -> RequestVoteResponse:
        return await self.request_vote(peer_id, term, last_log_index, last_log_term)
