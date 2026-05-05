"""Circuit breaker pattern for retryctl.

Prevents repeated attempts when a command is consistently failing,
opening the circuit after a threshold of consecutive failures.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking attempts
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerTripped(Exception):
    """Raised when an attempt is blocked by an open circuit."""

    def __init__(self, state: CircuitState, reset_at: Optional[float] = None) -> None:
        self.state = state
        self.reset_at = reset_at
        remaining = f"{reset_at - time.monotonic():.1f}s" if reset_at else "unknown"
        super().__init__(f"Circuit is {state.value}; retry blocked (resets in {remaining})")


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    half_open_max_attempts: int = 1

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.recovery_timeout <= 0:
            raise ValueError("recovery_timeout must be > 0")
        if self.half_open_max_attempts < 1:
            raise ValueError("half_open_max_attempts must be >= 1")


@dataclass
class CircuitBreaker:
    config: CircuitBreakerConfig
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _consecutive_failures: int = field(default=0, init=False)
    _opened_at: Optional[float] = field(default=None, init=False)
    _half_open_attempts: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self.config.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_attempts = 0
        return self._state

    def allow_attempt(self) -> None:
        """Raise CircuitBreakerTripped if the circuit blocks this attempt."""
        s = self.state
        if s == CircuitState.OPEN:
            reset_at = (self._opened_at or 0) + self.config.recovery_timeout
            raise CircuitBreakerTripped(s, reset_at=reset_at)
        if s == CircuitState.HALF_OPEN:
            if self._half_open_attempts >= self.config.half_open_max_attempts:
                raise CircuitBreakerTripped(s)
            self._half_open_attempts += 1

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._state = CircuitState.CLOSED
        self._opened_at = None

    def record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._state == CircuitState.HALF_OPEN or (
            self._consecutive_failures >= self.config.failure_threshold
        ):
            self._state = CircuitState.OPEN
            self._opened_at = time.monotonic()
