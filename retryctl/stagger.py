"""Stagger module: spread retries across a time window to avoid thundering herd."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StaggerConfig:
    """Configuration for stagger behaviour."""

    window: float  # seconds — total spread window
    key: str = "default"  # logical group key for isolation
    seed: Optional[int] = None  # optional RNG seed for deterministic tests

    def __post_init__(self) -> None:
        if self.window <= 0:
            raise ValueError("window must be positive")
        if not self.key or not self.key.strip():
            raise ValueError("key must not be blank")


@dataclass
class StaggerState:
    """Mutable state for a stagger group."""

    config: StaggerConfig
    _rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self._rng = random.Random(self.config.seed)

    def next_offset(self) -> float:
        """Return a random offset in [0, window) seconds."""
        return self._rng.uniform(0.0, self.config.window)

    @property
    def key(self) -> str:
        return self.config.key


class StaggerViolation(Exception):
    """Raised when a stagger offset cannot be applied (e.g. budget exceeded)."""

    def __init__(self, key: str, offset: float) -> None:
        self.key = key
        self.offset = offset
        super().__init__(f"stagger[{key}]: offset {offset:.3f}s could not be applied")


def apply_stagger(state: StaggerState, sleep_fn=None) -> float:
    """Compute and apply the stagger offset.  Returns the offset used."""
    import time

    _sleep = sleep_fn if sleep_fn is not None else time.sleep
    offset = state.next_offset()
    _sleep(offset)
    return offset
