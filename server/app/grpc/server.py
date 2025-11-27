from typing import TYPE_CHECKING

import grpc.aio as grpc

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

if TYPE_CHECKING:
    from app.raft.node import RaftNode


class RaftServices(RaftNodeServicer):
    def __init__(self, raft_node: RaftNode):
        self.node = raft_node

    async def RequestVote(self, request: RequestVoteRequest, context) -> RequestVoteResponse:
        await self.node.election_timeout.reset()

        if request.term > self.node.raft.current_term:
            self.node.raft.become_follower(request.term, leader=None)

        lli = self.node.last_log_index()
        llt = self.node.last_log_term()

        vote_granted = False
        up_to_date = request.last_log_term > llt or (
            request.last_log_term == llt and request.last_log_index >= lli
        )

        if (
            request.term == self.node.raft.current_term
            and up_to_date
            and (self.node.raft.voted_for in (None, request.candidate_id))
        ):
            self.node.raft.voted_for = request.candidate_id
            vote_granted = True
            self.node.raft.leader_id = None

        return RequestVoteResponse(term=self.node.raft.current_term, vote_granted=vote_granted)

    async def AppendEntries(self, request: AppendEntriesRequest, context) -> AppendEntriesResponse:
        if request.term < self.node.raft.current_term:
            return AppendEntriesResponse(
                term=self.node.raft.current_term, success=False, match_index=-1
            )

        await self.node.election_timeout.reset()

        if request.term > self.node.raft.current_term or self.node.raft.state_name != "follower":
            self.node.raft.become_follower(request.term, leader=request.leader_id)
        else:
            self.node.raft.leader_id = request.leader_id

        if request.prev_log_index > self.node.last_log_index():
            return AppendEntriesResponse(
                term=self.node.raft.current_term,
                success=False,
                match_index=self.node.last_log_index(),
            )

        def get_term_at(idx: int) -> int:
            if idx == 0:
                return 0
            if 1 <= idx <= self.node.last_log_index():
                return self.node.raft.log[idx - 1].term
            return -1

        if request.prev_log_index > 0:
            if get_term_at(request.prev_log_index) != request.prev_log_term:
                self.node.raft.log = self.node.raft.log[: request.prev_log_index - 1]
                return AppendEntriesResponse(
                    term=self.node.raft.current_term,
                    success=False,
                    match_index=self.node.last_log_index(),
                )

        for entry in request.entries:
            if entry.index <= self.node.last_log_index():
                if get_term_at(entry.index) != entry.term:
                    self.node.raft.log = self.node.raft.log[: entry.index - 1]
                    self.node.raft.log.append(entry)
                    await self.node.apply_command(entry.command, entry.data)
            else:
                self.node.raft.log.append(entry)
                await self.node.apply_command(entry.command, entry.data)

        if request.leader_commit > self.node.raft.commit_index:
            self.node.raft.commit_index = min(request.leader_commit, self.node.last_log_index())

        return AppendEntriesResponse(
            term=self.node.raft.current_term,
            success=True,
            match_index=self.node.last_log_index(),
        )

    async def HealthCheck(self, request: HealthCheckRequest, context) -> HealthCheckResponse:
        return HealthCheckResponse(node_id=self.node.node_id, status=await self.node.get_status())

    async def SetPixel(self, request: SetPixelRequest, context) -> SetPixelResponse:
        assert self.node.raft.leader_id == self.node.node_id, (
            "SetPixel can only be called on the leader"
        )
        await self.node.set_pixel(request.x, request.y, request.color, request.user_id)
        return SetPixelResponse(status="ok")


async def serve(raft_node: "RaftNode") -> None:
    server = grpc.server()
    services = RaftServices(raft_node)
    add_RaftNodeServicer_to_server(services, server)
    listen_addr = f"{raft_node.node_id}:50051"
    server.add_insecure_port(listen_addr)
    await server.start()
    await server.wait_for_termination()
