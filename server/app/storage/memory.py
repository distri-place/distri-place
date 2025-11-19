class InMemoryStorage:
    def __init__(self):
        self.data = {}
        self.commit_index = 0
        self.last_applied = 0

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value):
        self.data[key] = value

    def delete(self, key: str):
        if key in self.data:
            del self.data[key]

    def get_commit_index(self) -> int:
        return self.commit_index

    def set_commit_index(self, index: int):
        self.commit_index = index

    def get_last_applied(self) -> int:
        return self.last_applied

    def set_last_applied(self, index: int):
        self.last_applied = index
