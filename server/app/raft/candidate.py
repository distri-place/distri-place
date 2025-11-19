class RaftCandidate:
    def __init__(self, node_id: str):
        self.node_id = node_id

    def start_election(self):
        pass

    def request_votes(self):
        pass

    def handle_vote_response(self, response):
        pass
