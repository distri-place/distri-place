import asyncio

import grpc.aio as grpc

from app.generated.grpc.messages_pb2 import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    HealthCheckRequest,
    HealthCheckResponse,
    LogEntry,
    RequestVoteRequest,
    RequestVoteResponse,
    SubmitPixelRequest,
    SubmitPixelResponse,
)
from app.generated.grpc.messages_pb2_grpc import RaftNodeStub
from app.schemas import PeerNode


class RaftClient:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self._channels: dict[str, grpc.Channel] = {}
        self._stubs: dict[str, RaftNodeStub] = {}

    def _get_stub(self, peer: PeerNode) -> RaftNodeStub:
        peer_key = f"{peer.host}:{peer.grpc_port}"
        if peer_key not in self._stubs:
            if peer_key not in self._channels:
                options = [
                    ("grpc.default_timeout_ms", 60000),
                    ("grpc.keepalive_time_ms", 30000),
                    ("grpc.keepalive_timeout_ms", 15000),
                    ("grpc.keepalive_permit_without_calls", 1),
                    ("grpc.http2.max_pings_without_data", 0),
                    ("grpc.http2.min_time_between_pings_ms", 10000),
                    ("grpc.http2.min_ping_interval_without_data_ms", 300000),
                ]
                self._channels[peer_key] = grpc.insecure_channel(peer.grpc_address, options=options)
            self._stubs[peer_key] = RaftNodeStub(self._channels[peer_key])
        return self._stubs[peer_key]

    async def request_vote(
        self, peer: PeerNode, term: int, last_log_index: int, last_log_term: int
    ) -> RequestVoteResponse:
        stub = self._get_stub(peer)
        request = RequestVoteRequest(
            term=term,
            candidate_id=self.node_id,
            last_log_index=last_log_index,
            last_log_term=last_log_term,
        )
        return await stub.RequestVote(request, timeout=30.0)

    async def append_entries(
        self,
        peer: PeerNode,
        term: int,
        leader_id: str,
        prev_log_index: int,
        prev_log_term: int,
        entries: list[LogEntry],
        leader_commit: int,
    ) -> AppendEntriesResponse:
        stub = self._get_stub(peer)
        request = AppendEntriesRequest(
            term=term,
            leader_id=leader_id,
            prev_log_index=prev_log_index,
            prev_log_term=prev_log_term,
            entries=entries,
            leader_commit=leader_commit,
        )
        return await stub.AppendEntries(request, timeout=30.0)

    async def health_check(self, peer: PeerNode) -> HealthCheckResponse:
        stub = self._get_stub(peer)
        request = HealthCheckRequest(node_id=self.node_id)
        return await stub.HealthCheck(request, timeout=15.0)

    async def submit_pixel(self, peer: PeerNode, x: int, y: int, color: int) -> SubmitPixelResponse:
        stub = self._get_stub(peer)
        request = SubmitPixelRequest(x=x, y=y, color=color)
        return await stub.SubmitPixel(request, timeout=30.0)

    async def broadcast_request_votes(
        self, peers: list[PeerNode], term: int, last_log_index: int, last_log_term: int
    ) -> list[RequestVoteResponse]:
        requests = [self.request_vote(peer, term, last_log_index, last_log_term) for peer in peers]
        results = await asyncio.gather(*requests, return_exceptions=True)

        return [resp for resp in results if isinstance(resp, RequestVoteResponse)]

    async def broadcast_health_checks(self, peers: list[PeerNode]) -> list[HealthCheckResponse]:
        requests = [self.health_check(peer) for peer in peers]
        results = await asyncio.gather(*requests, return_exceptions=True)
        return [resp for resp in results if isinstance(resp, HealthCheckResponse)]

    async def close_all(self):
        for channel in self._channels.values():
            await channel.close()
        self._channels.clear()
        self._stubs.clear()

    async def peer_request_vote(
        self, peer: PeerNode, term: int, last_log_index: int, last_log_term: int
    ) -> RequestVoteResponse:
        return await self.request_vote(peer, term, last_log_index, last_log_term)
