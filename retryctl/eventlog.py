"""Structured event log for recording retry lifecycle events."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EventLogEntry:
    event_type: str
    attempt: int
    timestamp: float = field(default_factory=time.time)
    exit_code: Optional[int] = None
    delay: Optional[float] = None
    message: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "event_type": self.event_type,
            "attempt": self.attempt,
            "timestamp": self.timestamp,
        }
        if self.exit_code is not None:
            d["exit_code"] = self.exit_code
        if self.delay is not None:
            d["delay"] = self.delay
        if self.message is not None:
            d["message"] = self.message
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EventLogEntry":
        return cls(
            event_type=data["event_type"],
            attempt=data["attempt"],
            timestamp=data.get("timestamp", time.time()),
            exit_code=data.get("exit_code"),
            delay=data.get("delay"),
            message=data.get("message"),
            extra=data.get("extra", {}),
        )


class EventLog:
    def __init__(self) -> None:
        self._entries: List[EventLogEntry] = []

    def record(self, entry: EventLogEntry) -> None:
        self._entries.append(entry)

    def entries(self) -> List[EventLogEntry]:
        return list(self._entries)

    def entries_by_type(self, event_type: str) -> List[EventLogEntry]:
        return [e for e in self._entries if e.event_type == event_type]

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)
