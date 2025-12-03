from typing import TYPE_CHECKING

import grpc.aio as grpc

from app.config import settings
from app.generated.grpc.messages_pb2 import (
    AppendEntriesRequest,
    AppendEntriesResponse,
    HealthCheckRequest,
    HealthCheckResponse,
    RequestVoteRequest,
    RequestVoteResponse,
    SetPixelRequest,
    SetPixelResponse,
)
from app.generated.grpc.messages_pb2_grpc import RaftNodeServicer, add_RaftNodeServicer_to_server
from app.raft.node import RaftNode


class RaftServices(RaftNodeServicer):
    def __init__(self, raft_node: RaftNode):
        self.node = raft_node

    async def RequestVote(self, request: RequestVoteRequest, context) -> RequestVoteResponse:
        await self.node._reset_election_timeout()

        if request.term > self.node.current_term:
            from app.raft.node import Role

            self.node.role = Role.FOLLOWER
            self.node.current_term = request.term
            self.node.voted_for = None
            self.node.leader_id = None

        lli = self.node.last_log_index()
        llt = self.node.last_log_term()

        vote_granted = False
        up_to_date = request.last_log_term > llt or (
            request.last_log_term == llt and request.last_log_index >= lli
        )

        if (
            request.term == self.node.current_term
            and up_to_date
            and (self.node.voted_for in (None, request.candidate_id))
        ):
            self.node.voted_for = request.candidate_id
            vote_granted = True
            self.node.leader_id = None

        return RequestVoteResponse(term=self.node.current_term, vote_granted=vote_granted)

    async def AppendEntries(self, request: AppendEntriesRequest, context) -> AppendEntriesResponse:
        if request.term < self.node.current_term:
            return AppendEntriesResponse(term=self.node.current_term, success=False, match_index=-1)

        await self.node._reset_election_timeout()

        if request.term > self.node.current_term or self.node.role.value != "follower":
            from app.raft.node import Role

            self.node.role = Role.FOLLOWER
            self.node.current_term = request.term
            self.node.voted_for = None
            self.node.leader_id = request.leader_id
        else:
            self.node.leader_id = request.leader_id

        if request.prev_log_index > self.node.last_log_index():
            return AppendEntriesResponse(
                term=self.node.current_term,
                success=False,
                match_index=self.node.last_log_index(),
            )

        def get_term_at(idx: int) -> int:
            if idx == 0:
                return 0
            if 1 <= idx <= self.node.last_log_index():
                return self.node.log[idx - 1].term
            return -1

        if request.prev_log_index > 0:
            if get_term_at(request.prev_log_index) != request.prev_log_term:
                self.node.log = self.node.log[: request.prev_log_index - 1]
                return AppendEntriesResponse(
                    term=self.node.current_term,
                    success=False,
                    match_index=self.node.last_log_index(),
                )

        for entry in request.entries:
            if entry.index <= self.node.last_log_index():
                if get_term_at(entry.index) != entry.term:
                    self.node.log = self.node.log[: entry.index - 1]
                    self.node.log.append(entry)
                    await self.node.apply_command(entry.command, entry.data)
            else:
                self.node.log.append(entry)
                await self.node.apply_command(entry.command, entry.data)

        if request.leader_commit > self.node.commit_index:
            self.node.commit_index = min(request.leader_commit, self.node.last_log_index())

        return AppendEntriesResponse(
            term=self.node.current_term,
            success=True,
            match_index=self.node.last_log_index(),
        )

    async def HealthCheck(self, request: HealthCheckRequest, context) -> HealthCheckResponse:
        return HealthCheckResponse(node_id=self.node.node_id, status=await self.node.get_status())

    async def SetPixel(self, request: SetPixelRequest, context) -> SetPixelResponse:
        assert self.node.leader_id == self.node.node_id, "SetPixel can only be called on the leader"
        await self.node.set_pixel(request.x, request.y, request.color, request.user_id)
        return SetPixelResponse(status="ok")


async def create_grpc_server(raft_node: RaftNode):
    server = grpc.server()
    services = RaftServices(raft_node)
    add_RaftNodeServicer_to_server(services, server)
    listen_addr = f"{settings.HOST}:{settings.GRPC_PORT}"
    server.add_insecure_port(listen_addr)
    await server.start()
    return server


async def run_grpc_server(raft_node: RaftNode):
    server = await create_grpc_server(raft_node)
    try:
        await server.wait_for_termination()
    finally:
        await server.stop(0.2)
