"""Timeout support for command execution."""

from __future__ import annotations

import signal
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator, Optional


class TimeoutExpired(Exception):
    """Raised when a command exceeds its allowed execution time."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds
        super().__init__(f"Command timed out after {seconds}s")


@dataclass(frozen=True)
class TimeoutConfig:
    """Configuration for per-attempt and overall run timeouts."""

    per_attempt: Optional[float] = None  # seconds; None means no limit
    total: Optional[float] = None  # seconds; None means no limit

    def __post_init__(self) -> None:
        if self.per_attempt is not None and self.per_attempt <= 0:
            raise ValueError("per_attempt timeout must be positive")
        if self.total is not None and self.total <= 0:
            raise ValueError("total timeout must be positive")


def _sigalrm_handler(signum: int, frame: object) -> None:  # noqa: ARG001
    raise TimeoutExpired(0)  # seconds filled in by context manager


@contextmanager
def attempt_timeout(seconds: Optional[float]) -> Generator[None, None, None]:
    """Context manager that raises TimeoutExpired if the block takes too long.

    Only functional on POSIX systems (uses SIGALRM).  On Windows the block
    runs without a timeout and no error is raised.
    """
    if seconds is None or not hasattr(signal, "SIGALRM"):
        yield
        return

    original_handler = signal.signal(signal.SIGALRM, _sigalrm_handler)
    # setitimer supports fractional seconds; alarm() only handles integers
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    except TimeoutExpired:
        raise TimeoutExpired(seconds)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, original_handler)


def deadline_remaining(start: float, total: Optional[float], elapsed: float) -> Optional[float]:
    """Return seconds remaining before the total deadline, or None if no deadline."""
    if total is None:
        return None
    remaining = total - elapsed
    return max(remaining, 0.0)
