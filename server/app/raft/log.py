from typing import overload

from app.generated.grpc.messages_pb2 import LogEntry


class RaftLog:
    def __init__(self):
        self._entries: list[LogEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    @overload
    def __getitem__(self, index: int) -> LogEntry: ...

    @overload
    def __getitem__(self, index: slice) -> list[LogEntry]: ...

    def __getitem__(self, index: int | slice) -> LogEntry | list[LogEntry]:
        return self._entries[index]

    def append(self, entry: LogEntry) -> None:
        self._entries.append(entry)

    def truncate_from(self, index: int) -> None:
        if index <= len(self._entries):
            self._entries = self._entries[: index - 1]

    @property
    def last_index(self) -> int:
        return len(self._entries) - 1

    @property
    def last_term(self) -> int:
        if not self._entries:
            return 0
        return self._entries[-1].term

    def term_at(self, index: int) -> int:
        if index < 0 or index >= len(self._entries):
            return 0
        return self._entries[index].term
