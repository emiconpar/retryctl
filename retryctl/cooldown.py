"""Cooldown enforcement between retry attempts.

Provides a configurable minimum quiet period after a final failure,
preventing immediate re-invocation of a command that has exhausted retries.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


class CooldownActive(Exception):
    """Raised when a cooldown period is still in effect."""

    def __init__(self, remaining: float) -> None:
        self.remaining = remaining
        super().__init__(
            f"Cooldown active: {remaining:.2f}s remaining before next attempt is allowed"
        )


@dataclass
class CooldownConfig:
    """Configuration for the cooldown enforcer."""

    duration: float  # seconds
    key: str = "default"

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError("duration must be positive")
        if not self.key:
            raise ValueError("key must not be empty")


@dataclass
class CooldownState:
    """Persisted state for a single cooldown key."""

    key: str
    expires_at: float  # UNIX timestamp
    duration: float

    def is_active(self, now: Optional[float] = None) -> bool:
        t = now if now is not None else time.monotonic()
        return t < self.expires_at

    def remaining(self, now: Optional[float] = None) -> float:
        t = now if now is not None else time.monotonic()
        return max(0.0, self.expires_at - t)


class CooldownEnforcer:
    """Tracks and enforces cooldown periods keyed by an arbitrary string."""

    def __init__(self) -> None:
        self._states: dict[str, CooldownState] = {}

    def record_failure(self, config: CooldownConfig, now: Optional[float] = None) -> None:
        """Record a final failure and start the cooldown clock."""
        t = now if now is not None else time.monotonic()
        self._states[config.key] = CooldownState(
            key=config.key,
            expires_at=t + config.duration,
            duration=config.duration,
        )

    def check(self, key: str, now: Optional[float] = None) -> None:
        """Raise CooldownActive if the key is still cooling down."""
        state = self._states.get(key)
        if state is not None and state.is_active(now):
            raise CooldownActive(state.remaining(now))

    def clear(self, key: str) -> None:
        """Manually clear a cooldown entry."""
        self._states.pop(key, None)

    def state_for(self, key: str) -> Optional[CooldownState]:
        """Return the current CooldownState for *key*, or None."""
        return self._states.get(key)
