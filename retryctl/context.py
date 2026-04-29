"""Execution context passed through the retry lifecycle."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class RetryContext:
    """Carries state about the current retry run for use by hooks and reporters."""

    command: List[str]
    """The command being executed."""

    max_attempts: int
    """Maximum number of attempts allowed."""

    attempt: int = 0
    """Current attempt number (1-based, 0 before first attempt)."""

    last_exit_code: Optional[int] = None
    """Exit code from the most recent attempt."""

    last_error: Optional[str] = None
    """Stderr output or error message from the most recent attempt."""

    elapsed: float = 0.0
    """Total elapsed seconds across all attempts so far."""

    delays: List[float] = field(default_factory=list)
    """Backoff delays (in seconds) applied between attempts."""

    # ------------------------------------------------------------------ #
    # Derived helpers
    # ------------------------------------------------------------------ #

    @property
    def attempts_remaining(self) -> int:
        """How many attempts are left (including any currently in-flight)."""
        return max(0, self.max_attempts - self.attempt)

    @property
    def total_delay(self) -> float:
        """Sum of all backoff delays applied so far."""
        return sum(self.delays)

    @property
    def is_final_attempt(self) -> bool:
        """True when the current attempt is the last one allowed."""
        return self.attempt >= self.max_attempts

    def record_delay(self, delay: float) -> None:
        """Append a delay value to the history."""
        self.delays.append(delay)

    def as_dict(self) -> dict:
        """Return a plain-dict snapshot suitable for logging or JSON output."""
        return {
            "command": self.command,
            "max_attempts": self.max_attempts,
            "attempt": self.attempt,
            "attempts_remaining": self.attempts_remaining,
            "last_exit_code": self.last_exit_code,
            "last_error": self.last_error,
            "elapsed": round(self.elapsed, 4),
            "total_delay": round(self.total_delay, 4),
            "is_final_attempt": self.is_final_attempt,
        }
