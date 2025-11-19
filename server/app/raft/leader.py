class RaftLeader:
    def __init__(self, node_id: str):
        self.node_id = node_id

    def send_heartbeat(self):
        pass

    def append_entries(self, entries: list):
        pass

    def handle_client_request(self, request):
        pass
