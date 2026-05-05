"""Concurrency limiter for capping simultaneous retry attempts."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field


class ConcurrencyLimitExceeded(Exception):
    """Raised when the concurrency limit has been reached."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        super().__init__(f"Concurrency limit of {limit} active attempts exceeded")


@dataclass
class ConcurrencyConfig:
    max_concurrent: int

    def __post_init__(self) -> None:
        if self.max_concurrent <= 0:
            raise ValueError("max_concurrent must be a positive integer")


@dataclass
class ConcurrencyLimiter:
    """Thread-safe sliding counter that enforces a maximum concurrency cap."""

    config: ConcurrencyConfig
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _active: int = field(default=0, init=False)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def acquire(self) -> None:
        """Increment the active counter or raise ConcurrencyLimitExceeded."""
        with self._lock:
            if self._active >= self.config.max_concurrent:
                raise ConcurrencyLimitExceeded(self.config.max_concurrent)
            self._active += 1

    def release(self) -> None:
        """Decrement the active counter (never goes below zero)."""
        with self._lock:
            self._active = max(0, self._active - 1)

    @property
    def active(self) -> int:
        """Return the current number of active attempts."""
        with self._lock:
            return self._active

    # ------------------------------------------------------------------
    # Context-manager convenience
    # ------------------------------------------------------------------

    def __enter__(self) -> "ConcurrencyLimiter":
        self.acquire()
        return self

    def __exit__(self, *_: object) -> None:
        self.release()
