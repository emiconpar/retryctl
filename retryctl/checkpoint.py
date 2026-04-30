"""Checkpoint support for persisting retry state across process restarts."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class CheckpointState:
    command: list[str]
    attempt: int
    total_delay: float
    last_exit_code: Optional[int]
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CheckpointState":
        return cls(
            command=data["command"],
            attempt=data["attempt"],
            total_delay=data["total_delay"],
            last_exit_code=data.get("last_exit_code"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


class CheckpointStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def save(self, state: CheckpointState) -> None:
        state.updated_at = time.time()
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state.to_dict(), indent=2))
        tmp.replace(self._path)

    def load(self) -> Optional[CheckpointState]:
        if not self._path.exists():
            return None
        try:
            data = json.loads(self._path.read_text())
            return CheckpointState.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def clear(self) -> None:
        if self._path.exists():
            self._path.unlink()

    @property
    def exists(self) -> bool:
        return self._path.exists()
