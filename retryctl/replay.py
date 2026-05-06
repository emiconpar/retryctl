"""Replay support: persist and re-run failed command invocations."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class ReplayEntry:
    """A single persisted failed invocation that can be replayed."""

    command: List[str]
    exit_code: int
    attempts: int
    created_at: float = field(default_factory=time.time)
    correlation_id: Optional[str] = None
    labels: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if d["labels"] is None:
            del d["labels"]
        if d["correlation_id"] is None:
            del d["correlation_id"]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ReplayEntry":
        return cls(
            command=data["command"],
            exit_code=data["exit_code"],
            attempts=data["attempts"],
            created_at=data.get("created_at", time.time()),
            correlation_id=data.get("correlation_id"),
            labels=data.get("labels"),
        )


@dataclass
class ReplayConfig:
    path: str
    max_entries: int = 100

    def __post_init__(self) -> None:
        if self.max_entries <= 0:
            raise ValueError("max_entries must be a positive integer")
        if not self.path or not self.path.strip():
            raise ValueError("path must be a non-empty string")


class ReplayQueue:
    """Append-only JSONL queue of failed invocations for later replay."""

    def __init__(self, config: ReplayConfig) -> None:
        self._config = config
        self._path = Path(config.path)

    def push(self, entry: ReplayEntry) -> None:
        """Append *entry* to the replay file, respecting max_entries."""
        existing = self.load()
        existing.append(entry)
        if len(existing) > self._config.max_entries:
            existing = existing[-self._config.max_entries :]
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as fh:
            for e in existing:
                fh.write(json.dumps(e.to_dict()) + "\n")

    def load(self) -> List[ReplayEntry]:
        """Return all persisted entries (oldest first)."""
        if not self._path.exists():
            return []
        entries: List[ReplayEntry] = []
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    entries.append(ReplayEntry.from_dict(json.loads(line)))
        return entries

    def clear(self) -> None:
        """Remove all persisted entries."""
        if self._path.exists():
            self._path.unlink()
