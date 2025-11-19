class RaftFollower:
    def __init__(self, node_id: str):
        self.node_id = node_id

    def handle_append_entries(self, request):
        pass

    def handle_vote_request(self, request):
        pass

    def check_election_timeout(self):
        pass
