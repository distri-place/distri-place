from app.generated.grpc.messages_pb2 import LogEntry


class RaftLog:
    def __init__(self):
        self.entries: list[LogEntry] = []

    def append(self, entry: LogEntry) -> None:
        self.entries.append(entry)

    def get_entry(self, index: int) -> LogEntry | None:
        if index <= 0 or index > len(self.entries):
            return None
        return self.entries[index - 1]

    def get_entries_after(self, index: int) -> list[LogEntry]:
        if index <= 0 or index > len(self.entries):
            return []
        return self.entries[index:]

    def get_last_log_index(self) -> int:
        return len(self.entries)

    def get_last_log_term(self) -> int:
        return 0 if not self.entries else self.entries[-1].term

    def get_term_at_index(self, index: int) -> int:
        if index == 0:
            return 0
        if 1 <= index <= len(self.entries):
            return self.entries[index - 1].term
        return -1

    def truncate_from(self, index: int) -> None:
        if index <= len(self.entries):
            self.entries = self.entries[: index - 1]

    def __len__(self) -> int:
        return len(self.entries)

    def __getitem__(self, index: int) -> LogEntry:
        return self.entries[index]
