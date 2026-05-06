"""Debounce support: suppress retries that fire too quickly in succession."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


class DebounceViolation(Exception):
    """Raised when a retry attempt is debounced (too soon after the last one)."""

    def __init__(self, wait_remaining: float) -> None:
        self.wait_remaining = wait_remaining
        super().__init__(
            f"Retry debounced: must wait {wait_remaining:.3f}s before next attempt"
        )


@dataclass
class DebounceConfig:
    """Configuration for debounce behaviour."""

    min_interval: float  # minimum seconds between consecutive retry attempts
    key: str = "default"

    def __post_init__(self) -> None:
        if self.min_interval <= 0:
            raise ValueError("min_interval must be positive")
        if not self.key or not self.key.strip():
            raise ValueError("key must not be blank")


@dataclass
class DebounceState:
    """Tracks the last attempt timestamp for a debounce key."""

    config: DebounceConfig
    _last_attempt: Optional[float] = field(default=None, init=False, repr=False)

    def record(self) -> None:
        """Record that an attempt just occurred."""
        self._last_attempt = time.monotonic()

    def check(self) -> None:
        """Raise DebounceViolation if the minimum interval has not elapsed."""
        if self._last_attempt is None:
            return
        elapsed = time.monotonic() - self._last_attempt
        remaining = self.config.min_interval - elapsed
        if remaining > 0:
            raise DebounceViolation(wait_remaining=remaining)

    def is_ready(self) -> bool:
        """Return True if enough time has passed since the last attempt."""
        try:
            self.check()
            return True
        except DebounceViolation:
            return False

    def seconds_until_ready(self) -> float:
        """Return how many seconds remain before the next attempt is allowed."""
        if self._last_attempt is None:
            return 0.0
        elapsed = time.monotonic() - self._last_attempt
        return max(0.0, self.config.min_interval - elapsed)
