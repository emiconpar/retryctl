"""Snapshot captures a point-in-time summary of a retry run for diffing or reporting."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SnapshotEntry:
    attempt: int
    exit_code: Optional[int]
    succeeded: bool
    delay_after: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "attempt": self.attempt,
            "exit_code": self.exit_code,
            "succeeded": self.succeeded,
            "delay_after": self.delay_after,
            "timestamp": self.timestamp,
        }
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SnapshotEntry":
        return cls(
            attempt=data["attempt"],
            exit_code=data.get("exit_code"),
            succeeded=data["succeeded"],
            delay_after=data["delay_after"],
            timestamp=data["timestamp"],
        )


@dataclass
class RunSnapshot:
    command: List[str]
    entries: List[SnapshotEntry] = field(default_factory=list)
    final_succeeded: bool = False
    created_at: float = field(default_factory=time.time)

    def record(self, entry: SnapshotEntry) -> None:
        self.entries.append(entry)

    def total_attempts(self) -> int:
        return len(self.entries)

    def total_delay(self) -> float:
        return sum(e.delay_after for e in self.entries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "final_succeeded": self.final_succeeded,
            "created_at": self.created_at,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunSnapshot":
        snap = cls(
            command=data["command"],
            final_succeeded=data["final_succeeded"],
            created_at=data["created_at"],
        )
        snap.entries = [SnapshotEntry.from_dict(e) for e in data.get("entries", [])]
        return snap
