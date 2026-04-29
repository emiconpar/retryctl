"""Retry budget: limits total number of retries across a sliding time window."""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


class BudgetExceeded(Exception):
    """Raised when the retry budget has been exhausted."""

    def __init__(self, max_retries: int, window: float) -> None:
        self.max_retries = max_retries
        self.window = window
        super().__init__(
            f"Retry budget exhausted: {max_retries} retries used within {window}s window"
        )


@dataclass
class BudgetConfig:
    max_retries: int
    window_seconds: float

    def __post_init__(self) -> None:
        if self.max_retries <= 0:
            raise ValueError("max_retries must be a positive integer")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


@dataclass
class RetryBudget:
    """Sliding-window retry budget tracker."""

    config: BudgetConfig
    _timestamps: deque[float] = field(default_factory=deque, init=False)

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self.config.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def remaining(self) -> int:
        """Return how many retries are still available in the current window."""
        self._evict_expired(time.monotonic())
        return max(0, self.config.max_retries - len(self._timestamps))

    def check_and_record(self) -> None:
        """Record a retry attempt, raising BudgetExceeded if the budget is exhausted."""
        now = time.monotonic()
        self._evict_expired(now)
        if len(self._timestamps) >= self.config.max_retries:
            raise BudgetExceeded(self.config.max_retries, self.config.window_seconds)
        self._timestamps.append(now)

    def reset(self) -> None:
        """Clear all recorded retries."""
        self._timestamps.clear()
