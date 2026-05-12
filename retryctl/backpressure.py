"""Backpressure detection and enforcement for retry operations.

Allows callers to signal that the downstream system is under load,
causing retryctl to pause or abort retries until pressure subsides.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional


class BackpressureTripped(Exception):
    """Raised when backpressure threshold is exceeded."""

    def __init__(self, message: str, pressure: float) -> None:
        super().__init__(message)
        self.pressure = pressure


@dataclass
class BackpressureConfig:
    """Configuration for backpressure detection."""

    max_pressure: float = 1.0
    """Pressure value (0.0–1.0) above which retries are blocked."""

    hold_duration: float = 5.0
    """Seconds to hold off retries once pressure is tripped."""

    key: str = "default"
    """Logical name for this backpressure guard."""

    def __post_init__(self) -> None:
        if not (0.0 < self.max_pressure <= 1.0):
            raise ValueError("max_pressure must be in (0.0, 1.0]")
        if self.hold_duration <= 0:
            raise ValueError("hold_duration must be positive")
        if not self.key or not self.key.strip():
            raise ValueError("key must not be blank")


@dataclass
class BackpressureState:
    """Runtime state for a single backpressure guard."""

    config: BackpressureConfig
    _pressure: float = field(default=0.0, init=False)
    _tripped_at: Optional[float] = field(default=None, init=False)
    _clock: Callable[[], float] = field(default=time.monotonic, init=False, repr=False)

    def update(self, pressure: float) -> None:
        """Update current pressure reading (0.0–1.0)."""
        if not (0.0 <= pressure <= 1.0):
            raise ValueError("pressure must be in [0.0, 1.0]")
        self._pressure = pressure
        if pressure > self.config.max_pressure and self._tripped_at is None:
            self._tripped_at = self._clock()

    def is_active(self) -> bool:
        """Return True if backpressure is currently blocking retries."""
        if self._tripped_at is None:
            return False
        elapsed = self._clock() - self._tripped_at
        if elapsed >= self.config.hold_duration:
            self._tripped_at = None
            self._pressure = 0.0
            return False
        return True

    def check(self) -> None:
        """Raise BackpressureTripped if backpressure is active."""
        if self.is_active():
            raise BackpressureTripped(
                f"Backpressure active for key '{self.config.key}' "
                f"(pressure={self._pressure:.2f})",
                pressure=self._pressure,
            )

    @property
    def current_pressure(self) -> float:
        return self._pressure
