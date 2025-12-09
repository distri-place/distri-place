import logging

import grpc.aio as grpc

from app.config import settings
from app.generated.grpc.messages_pb2 import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    HealthCheckRequest,
    HealthCheckResponse,
    RequestVoteRequest,
    RequestVoteResponse,
    SubmitPixelRequest,
    SubmitPixelResponse,
)
from app.generated.grpc.messages_pb2_grpc import RaftNodeServicer, add_RaftNodeServicer_to_server
from app.raft.node import RaftNode

logger = logging.getLogger(__name__)


class RaftServices(RaftNodeServicer):
    def __init__(self, raft_node: RaftNode):
        self.node = raft_node

    async def RequestVote(self, request: RequestVoteRequest, context) -> RequestVoteResponse:
        term, vote_granted = self.node.on_request_vote(
            term=request.term,
            candidate_id=request.candidate_id,
            last_log_index=request.last_log_index,
            last_log_term=request.last_log_term,
        )

        return RequestVoteResponse(
            term=term,
            vote_granted=vote_granted,
        )

    async def AppendEntries(self, request: AppendEntriesRequest, context) -> AppendEntriesResponse:
        term, success = self.node.on_append_entries(
            term=request.term,
            leader_id=request.leader_id,
            prev_log_index=request.prev_log_index,
            prev_log_term=request.prev_log_term,
            entries=list(request.entries),
            leader_commit=request.leader_commit,
        )

        return AppendEntriesResponse(
            term=term,
            success=success,
        )

    async def HealthCheck(self, request: HealthCheckRequest, context) -> HealthCheckResponse:
        return HealthCheckResponse(node_id=self.node.node_id, status="ok")

    async def SubmitPixel(self, request: SubmitPixelRequest, context) -> SubmitPixelResponse:
        await self.node.submit_pixel(request.x, request.y, request.color)
        return SubmitPixelResponse(success=True)


async def run_grpc_server(raft_node: RaftNode) -> grpc.Server:
    server = grpc.server()
    services = RaftServices(raft_node)

    add_RaftNodeServicer_to_server(services, server)

    listen_addr = f"{settings.HOST}:{settings.GRPC_PORT}"
    server.add_insecure_port(listen_addr)

    await server.start()
    logger.info(f"gRPC server started on {listen_addr}")

    return server
