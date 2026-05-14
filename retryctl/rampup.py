"""Gradual ramp-up of retry concurrency/rate over time."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import time


class RampUpExceeded(Exception):
    def __init__(self, allowed: int, attempted: int) -> None:
        self.allowed = allowed
        self.attempted = attempted
        super().__init__(
            f"Ramp-up limit reached: allowed {allowed}, attempted {attempted}"
        )


@dataclass
class RampUpConfig:
    initial_limit: int
    max_limit: int
    step: int
    step_interval: float  # seconds between steps
    key: str = "default"

    def __post_init__(self) -> None:
        if self.initial_limit < 1:
            raise ValueError("initial_limit must be >= 1")
        if self.max_limit < self.initial_limit:
            raise ValueError("max_limit must be >= initial_limit")
        if self.step < 1:
            raise ValueError("step must be >= 1")
        if self.step_interval <= 0:
            raise ValueError("step_interval must be > 0")
        if not self.key or not self.key.strip():
            raise ValueError("key must not be blank")


@dataclass
class RampUpState:
    config: RampUpConfig
    _started_at: float = field(default_factory=time.monotonic)
    _attempt_count: int = 0
    _clock: object = field(default=None, repr=False)

    def _now(self) -> float:
        if self._clock is not None:
            return self._clock()
        return time.monotonic()

    @property
    def current_limit(self) -> int:
        elapsed = self._now() - self._started_at
        steps_taken = int(elapsed / self.config.step_interval)
        limit = self.config.initial_limit + steps_taken * self.config.step
        return min(limit, self.config.max_limit)

    def check(self) -> None:
        self._attempt_count += 1
        limit = self.current_limit
        if self._attempt_count > limit:
            raise RampUpExceeded(allowed=limit, attempted=self._attempt_count)

    def reset(self) -> None:
        self._attempt_count = 0
        self._started_at = self._now()
