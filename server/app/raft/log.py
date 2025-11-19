class RaftLog:
    def __init__(self):
        self.entries = []

    def append(self, entry):
        pass

    def get_entry(self, index: int):
        pass

    def get_last_log_index(self) -> int:
        pass

    def get_last_log_term(self) -> int:
        pass

