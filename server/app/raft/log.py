from typing import overload

from app.generated.grpc.messages_pb2 import LogEntry


class RaftLog:
    """One indexed raft log"""

    def __init__(self):
        self._entries: list[LogEntry] = []

    def __len__(self) -> int:
        return len(self._entries)

    @overload
    def __getitem__(self, index: int) -> LogEntry: ...

    @overload
    def __getitem__(self, index: slice) -> list[LogEntry]: ...

    def __getitem__(self, index: int | slice) -> LogEntry | list[LogEntry]:
        if isinstance(index, int):
            return self._entries[index - 1]
        if isinstance(index, slice):
            start = (index.start - 1) if index.start is not None else None
            stop = (index.stop) if index.stop is not None else None
            return self._entries[start:stop]

    def append(self, entry: LogEntry) -> None:
        self._entries.append(entry)

    def truncate_from(self, index: int) -> None:
        if index <= len(self._entries) + 1:
            self._entries = self._entries[: index - 1]

    @property
    def last_index(self) -> int:
        return len(self._entries)

    @property
    def last_term(self) -> int:
        if not self._entries:
            return 0
        return self._entries[-1].term

    def term_at(self, index: int) -> int:
        if index < 1 or index > len(self._entries):
            return 0
        return self._entries[index - 1].term
