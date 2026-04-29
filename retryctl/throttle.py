"""Rate limiting / throttle support for retryctl.

Allows capping how many retry attempts can be made within a rolling
time window so that a misbehaving command does not hammer a downstream
service.
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class ThrottleConfig:
    """Configuration for the sliding-window rate limiter."""

    max_attempts: int
    """Maximum number of attempts allowed within *window_seconds*."""

    window_seconds: float
    """Length of the rolling window in seconds."""

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")


class ThrottleExceeded(Exception):
    """Raised when the retry rate limit has been reached."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Throttle limit exceeded; retry after {retry_after:.2f}s"
        )


class SlidingWindowThrottle:
    """Sliding-window rate limiter.

    Call :meth:`record` after each attempt.  Call :meth:`check` before
    scheduling a new attempt; it raises :exc:`ThrottleExceeded` when the
    window is saturated.
    """

    def __init__(self, config: ThrottleConfig) -> None:
        self._config = config
        self._timestamps: Deque[float] = deque()

    # ------------------------------------------------------------------
    def _evict_old(self, now: float) -> None:
        cutoff = now - self._config.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def record(self, ts: float | None = None) -> None:
        """Record that an attempt occurred at *ts* (default: now)."""
        self._timestamps.append(ts if ts is not None else time.monotonic())

    def check(self, ts: float | None = None) -> None:
        """Raise :exc:`ThrottleExceeded` if the window is saturated."""
        now = ts if ts is not None else time.monotonic()
        self._evict_old(now)
        if len(self._timestamps) >= self._config.max_attempts:
            oldest = self._timestamps[0]
            retry_after = (oldest + self._config.window_seconds) - now
            raise ThrottleExceeded(max(retry_after, 0.0))

    @property
    def current_count(self) -> int:
        """Number of attempts recorded within the current window."""
        self._evict_old(time.monotonic())
        return len(self._timestamps)
