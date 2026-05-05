"""Dead-letter queue: persist failed command runs for later inspection or replay."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


@dataclass
class DeadLetterEntry:
    command: List[str]
    exit_code: Optional[int]
    attempts: int
    failed_at: float = field(default_factory=time.time)
    reason: Optional[str] = None
    labels: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DeadLetterEntry":
        return cls(**data)


@dataclass
class DeadLetterConfig:
    path: str
    max_entries: int = 500

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            raise ValueError("max_entries must be at least 1")


class DeadLetterQueue:
    def __init__(self, config: DeadLetterConfig) -> None:
        self._config = config
        self._store = Path(config.path)
        self._store.mkdir(parents=True, exist_ok=True)

    def push(self, entry: DeadLetterEntry) -> None:
        entries = self._load()
        entries.append(entry.to_dict())
        if len(entries) > self._config.max_entries:
            entries = entries[-self._config.max_entries :]
        self._save(entries)

    def all(self) -> List[DeadLetterEntry]:
        return [DeadLetterEntry.from_dict(d) for d in self._load()]

    def clear(self) -> None:
        self._save([])

    def _file(self) -> Path:
        return self._store / "dead_letter.json"

    def _load(self) -> list:
        f = self._file()
        if not f.exists():
            return []
        with f.open() as fh:
            return json.load(fh)

    def _save(self, entries: list) -> None:
        with self._file().open("w") as fh:
            json.dump(entries, fh, indent=2)
