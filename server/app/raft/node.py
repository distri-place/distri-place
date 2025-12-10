from __future__ import annotations

import asyncio
from enum import Enum
import logging
import random

from app.canvas.state import Canvas
from app.generated.grpc.messages_pb2 import LogEntry
from app.grpc.client import RaftClient
from app.raft.log import RaftLog
from app.schemas import PeerNode

logger = logging.getLogger(__name__)


class Role(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class RaftNode:
    def __init__(self, node_id: str, peers: list[PeerNode], canvas: Canvas):
        self.canvas = canvas
        self.grpc_client = RaftClient(node_id)

        self.node_id = node_id
        self.role = Role.FOLLOWER
        self.leader_id: str | None = None

        # Persistent for all
        self.current_term = 0
        self.voted_for: str | None = None
        self.log = RaftLog()

        # Volatile for all
        self.commit_index = 0
        self.last_applied = 0
        self.peers = peers

        # Volatile for leaders
        self.next_index: dict[str, int] | None = None
        self.match_index: dict[str, int] | None = None
        self._pending_commits: dict[int, asyncio.Future[bool]] | None = None

        self._election_timeout = random.uniform(1.5, 3.0)
        self._last_heartbeat = asyncio.get_event_loop().time()

    async def start(self):
        logger.debug(f"Node {self.node_id}: called start()")
        while True:
            if self.role == Role.LEADER:
                await self._leader_loop()
            else:
                await self._follower_candidate_loop()

    async def _follower_candidate_loop(self):
        logger.debug(f"Node {self.node_id}: called _follower_candidate_loop()")
        while self.role in (Role.FOLLOWER, Role.CANDIDATE):
            now = asyncio.get_event_loop().time()
            elapsed = now - self._last_heartbeat

            if elapsed >= self._election_timeout:
                await self._start_election()

            await asyncio.sleep(0.1)

    async def _leader_loop(self):
        logger.debug(f"Node {self.node_id}: called _leader_loop()")
        while self.role == Role.LEADER:
            await self._send_heartbeats()
            await asyncio.sleep(1.0)

    async def _start_election(self):
        logger.debug(f"Node {self.node_id}: called _start_election()")
        self.role = Role.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id

        # Reset election
        self._election_timeout = random.uniform(1.5, 3.0)
        self._last_heartbeat = asyncio.get_event_loop().time()

        term = self.current_term
        votes = 1

        last_log_index = self.log.last_index
        last_log_term = self.log.last_term

        if self.current_term != term or self.role != Role.CANDIDATE:
            return

        responses = await self.grpc_client.broadcast_request_votes(
            self.peers, self.current_term, last_log_index, last_log_term
        )

        for response in responses:
            if response.term > self.current_term:
                self._become_follower(response.term)
                return
            if response.vote_granted:
                votes += 1
                continue

        majority = (len(self.peers) + 1) // 2 + 1
        if votes >= majority:
            self._become_leader()

    def _become_leader(self):
        logger.debug(f"Node {self.node_id}: called _become_leader()")
        self.role = Role.LEADER
        self.leader_id = self.node_id

        self.next_index = {p.node_id: self.log.last_index + 1 for p in self.peers}
        self.match_index = {p.node_id: 0 for p in self.peers}
        self._pending_commits = {}

    def _become_follower(self, term: int):
        logger.debug(f"Node {self.node_id}: called _become_follower(term={term})")
        self.role = Role.FOLLOWER
        self.current_term = term
        self.voted_for = None
        self._last_heartbeat = asyncio.get_event_loop().time()
        self._pending_commits = None
        self.next_index = None
        self.match_index = None

    async def _send_heartbeats(self):
        logger.debug(f"Node {self.node_id}: called _send_heartbeats()")
        logger.debug(f"Node {self.node_id}: match_index state: {self.match_index}")
        tasks = [self._send_append_entries(peer) for peer in self.peers]
        await asyncio.gather(*tasks, return_exceptions=True)
        self._try_advance_commit_index()

    async def _send_append_entries(self, peer: PeerNode):
        logger.debug(f"Node {self.node_id}: called _send_append_entries(peer={peer.node_id})")
        if self.role != Role.LEADER or self.next_index is None or self.match_index is None:
            return

        next_idx = self.next_index[peer.node_id]
        prev_log_index = next_idx - 1
        prev_log_term = self.log.term_at(prev_log_index)

        entries = self.log[next_idx:]

        try:
            resp = await self.grpc_client.append_entries(
                peer,
                term=self.current_term,
                leader_id=self.node_id,
                prev_log_index=prev_log_index,
                prev_log_term=prev_log_term,
                entries=entries,
                leader_commit=self.commit_index,
            )
            logger.debug(f"Node {self.node_id}: append_entries to {peer.node_id} succeeded: term={resp.term}, success={resp.success}")
        except Exception as e:
            logger.debug(f"Node {self.node_id}: append_entries to {peer.node_id} failed: {e}")
            return

        if resp.term > self.current_term:
            self._become_follower(resp.term)
            return

        if resp.success:
            self.next_index[peer.node_id] = next_idx + len(entries)
            self.match_index[peer.node_id] = self.next_index[peer.node_id] - 1
        else:
            self.next_index[peer.node_id] = max(1, next_idx - 1)

    def _get_peer(self, node_id: str) -> PeerNode | None:
        logger.debug(f"Node {self.node_id}: called _get_peer(node_id={node_id})")
        for peer in self.peers:
            if peer.node_id == node_id:
                return peer
        return None

    def _try_advance_commit_index(self):
        if self.role != Role.LEADER or self.match_index is None or self.next_index is None:
            return

        for n in range(self.commit_index + 1, len(self.log) + 1):
            if self.log.term_at(n) != self.current_term:
                continue

            replicated = 1
            replicated_peers = []
            for peer in self.peers:
                if self.match_index.get(peer.node_id, 0) >= n:
                    replicated += 1
                    replicated_peers.append(peer.node_id)

            majority = (len(self.peers) + 1) // 2 + 1
            logger.debug(
                f"Node {self.node_id}: index={n}, replicated={replicated}/{majority} (peers: {replicated_peers})"
            )
            if replicated >= majority:
                self.commit_index = n
                logger.debug(f"Node {self.node_id}: committed index {n}")

        self._apply_committed()

    def _apply_committed(self):
        logger.debug(f"Node {self.node_id}: called _apply_committed()")
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            self.canvas.update(entry.x, entry.y, entry.color)

            if (
                self.role == Role.LEADER
                and self._pending_commits is not None
                and entry.index in self._pending_commits
            ):
                self._pending_commits.pop(entry.index).set_result(True)

    # handlers
    def on_append_entries(
        self,
        term: int,
        leader_id: str,
        prev_log_index: int,
        prev_log_term: int,
        entries: list[LogEntry],
        leader_commit: int,
    ) -> tuple[int, bool]:
        logger.debug(
            f"Node {self.node_id}: called on_append_entries(term={term}, leader_id={leader_id})"
        )
        self._last_heartbeat = asyncio.get_event_loop().time()

        if term < self.current_term:
            return self.current_term, False

        if term > self.current_term or self.role == Role.CANDIDATE:
            self._become_follower(term)

        self.leader_id = leader_id

        if prev_log_index > 0:
            if prev_log_index > len(self.log):
                return self.current_term, False
            if self.log[prev_log_index].term != prev_log_term:
                return self.current_term, False

        for entry in entries:
            if entry.index <= len(self.log):
                if self.log[entry.index].term != entry.term:
                    self.log.truncate_from(entry.index)
                    self.log.append(entry)
            else:
                self.log.append(entry)

        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, self.log.last_index)
            self._apply_committed()

        return self.current_term, True

    def on_request_vote(
        self, term: int, candidate_id: str, last_log_index: int, last_log_term: int
    ) -> tuple[int, bool]:
        logger.debug(
            f"Node {self.node_id}: called on_request_vote(term={term}, candidate_id={candidate_id})"
        )
        if term < self.current_term:
            return self.current_term, False

        if term > self.current_term:
            self._become_follower(term)

        vote_granted = False
        if self.voted_for in (None, candidate_id):
            my_last_index = self.log.last_index
            my_last_term = self.log.last_term

            log_ok = last_log_term > my_last_term or (
                last_log_term == my_last_term and last_log_index >= my_last_index
            )

            if log_ok:
                logger.debug(
                    f"Node {self.node_id}: granting vote to {candidate_id} for term {term}"
                )
                self.voted_for = candidate_id
                self._last_heartbeat = asyncio.get_event_loop().time()
                vote_granted = True

        return self.current_term, vote_granted

    # API
    async def submit_pixel(self, x: int, y: int, color: int) -> bool:
        logger.debug(f"Node {self.node_id}: called submit_pixel(x={x}, y={y}, color={color})")
        logger.debug(f"Node {self.node_id}: role={self.role.name}, leader_id={self.leader_id}")
        if self.role == Role.LEADER:
            if self._pending_commits is None or self.next_index is None:
                logger.debug(f"Node {self.node_id}: leader missing required state, returning False")
                return False

            logger.debug(f"Node {self.node_id}: leader processing pixel submission")
            entry = LogEntry(
                term=self.current_term,
                index=self.log.last_index + 1,
                x=x,
                y=y,
                color=color,
            )
            self.log.append(entry)
            logger.debug(f"Node {self.node_id}: added entry to log at index {entry.index}")

            future = asyncio.get_event_loop().create_future()
            self._pending_commits[entry.index] = future

            try:
                logger.debug(f"Node {self.node_id}: waiting for commit with 30s timeout")
                result = await asyncio.wait_for(future, timeout=30.0)
                logger.debug(f"Node {self.node_id}: commit completed with result={result}")
                return result
            except TimeoutError:
                logger.debug(f"Node {self.node_id}: commit timed out after 30s")
                if self._pending_commits is not None and entry.index in self._pending_commits:
                    del self._pending_commits[entry.index]
                return False
        else:
            if not self.leader_id:
                logger.debug(f"Node {self.node_id}: no leader_id, returning False")
                return False

            leader_peer = self._get_peer(self.leader_id)
            if leader_peer:
                try:
                    logger.debug(f"Node {self.node_id}: forwarding to leader {self.leader_id}")
                    response = await self.grpc_client.submit_pixel(leader_peer, x, y, color)
                    logger.debug(f"Node {self.node_id}: leader response success={response.success}")
                    return response.success
                except Exception as e:
                    logger.debug(f"Node {self.node_id}: exception forwarding to leader: {e}")
                    return False
            logger.debug(
                f"Node {self.node_id}: leader_peer not found for leader_id={self.leader_id}"
            )
            return False
