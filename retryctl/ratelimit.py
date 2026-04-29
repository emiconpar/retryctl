"""Rate limiting support for retryctl — caps the number of attempts per time window."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque


class RateLimitExceeded(Exception):
    """Raised when the rate limit has been exceeded."""

    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after:.2f}s.")


@dataclass
class RateLimitConfig:
    """Configuration for a token-bucket-style rate limiter."""

    max_attempts: int
    window_seconds: float

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be a positive integer")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


class SlidingWindowRateLimiter:
    """Tracks attempt timestamps in a sliding window to enforce a rate limit."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._timestamps: Deque[float] = deque()

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self._config.window_seconds
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

    def is_allowed(self) -> bool:
        """Return True if another attempt is permitted right now."""
        now = time.monotonic()
        self._evict_expired(now)
        return len(self._timestamps) < self._config.max_attempts

    def record(self) -> None:
        """Record that an attempt has been made."""
        self._timestamps.append(time.monotonic())

    def check_and_record(self) -> None:
        """Record an attempt or raise RateLimitExceeded if the limit is hit."""
        now = time.monotonic()
        self._evict_expired(now)
        if len(self._timestamps) >= self._config.max_attempts:
            oldest = self._timestamps[0]
            retry_after = self._config.window_seconds - (now - oldest)
            raise RateLimitExceeded(retry_after=max(retry_after, 0.0))
        self._timestamps.append(now)

    @property
    def current_count(self) -> int:
        """Number of attempts recorded within the current window."""
        self._evict_expired(time.monotonic())
        return len(self._timestamps)
