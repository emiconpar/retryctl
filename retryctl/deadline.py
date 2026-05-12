"""Deadline enforcement: abort the entire retry run if a wall-clock deadline is exceeded."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


class DeadlineExceeded(Exception):
    """Raised when the overall run deadline has been exceeded."""

    def __init__(self, deadline_at: float, now: float) -> None:
        self.deadline_at = deadline_at
        self.now = now
        overrun = now - deadline_at
        super().__init__(f"Run deadline exceeded by {overrun:.3f}s")


@dataclass
class DeadlineConfig:
    """Configuration for deadline enforcement."""

    max_duration: float  # seconds; total wall-clock budget for the whole run
    clock: object = field(default=None, repr=False)  # injectable for testing

    def __post_init__(self) -> None:
        if self.max_duration <= 0:
            raise ValueError("max_duration must be positive")


@dataclass
class DeadlineState:
    """Tracks the start time and enforces the deadline."""

    config: DeadlineConfig
    _started_at: float = field(init=False)

    def __post_init__(self) -> None:
        self._started_at = self._now()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(self) -> None:
        """Raise DeadlineExceeded if the deadline has passed."""
        now = self._now()
        deadline_at = self._started_at + self.config.max_duration
        if now >= deadline_at:
            raise DeadlineExceeded(deadline_at=deadline_at, now=now)

    def remaining(self) -> float:
        """Return seconds remaining before the deadline (may be negative)."""
        return (self._started_at + self.config.max_duration) - self._now()

    def elapsed(self) -> float:
        """Return seconds elapsed since the run started."""
        return self._now() - self._started_at

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _now(self) -> float:
        if self.config.clock is not None:
            return self.config.clock()
        return time.monotonic()
