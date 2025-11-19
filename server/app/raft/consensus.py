from app.raft.candidate import RaftCandidate
from app.raft.follower import RaftFollower
from app.raft.leader import RaftLeader


class RaftConsensus:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.current_term = 0
        self.voted_for = None
        self.state_handler = RaftFollower(node_id)

    def become_leader(self):
        self.state_handler = RaftLeader(self.node_id)

    def become_candidate(self):
        self.state_handler = RaftCandidate(self.node_id)

    def become_follower(self, term: int):
        self.current_term = term
        self.voted_for = None
        self.state_handler = RaftFollower(self.node_id)

    @property
    def state_name(self) -> str:
        return self.state_handler.__class__.__name__.replace("Raft", "").lower()
