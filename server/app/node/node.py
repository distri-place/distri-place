class Node:
    def __init__(self, node_id: str, peers: list = None):
        self.node_id = node_id
        self.peers = peers or []

    def start(self):
        pass

    def stop(self):
        pass

    def get_status(self):
        pass

