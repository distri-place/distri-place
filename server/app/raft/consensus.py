from enum import Enum


class RaftState(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class RaftConsensus:
    def __init__(self, node_id: str):
        self.node_id = node_id
        self.state = RaftState.FOLLOWER
        self.current_term = 0
        self.voted_for = None

    def become_leader(self):
        pass

    def become_candidate(self):
        pass

    def become_follower(self, term: int):
        pass
