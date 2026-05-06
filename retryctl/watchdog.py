"""Watchdog: detect and respond to stalled/hung commands during retry execution."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, Optional


class WatchdogTripped(Exception):
    """Raised when the watchdog detects a stalled command."""

    def __init__(self, key: str, stall_timeout: float) -> None:
        self.key = key
        self.stall_timeout = stall_timeout
        super().__init__(
            f"Watchdog '{key}' tripped: no progress detected within {stall_timeout}s"
        )


@dataclass
class WatchdogConfig:
    stall_timeout: float  # seconds without a heartbeat before tripping
    key: str = "default"
    enabled: bool = True

    def __post_init__(self) -> None:
        if self.stall_timeout <= 0:
            raise ValueError("stall_timeout must be positive")
        if not self.key or not self.key.strip():
            raise ValueError("key must not be blank")


class Watchdog:
    """Timer-based watchdog that trips if not fed within stall_timeout seconds."""

    def __init__(self, config: WatchdogConfig, on_trip: Callable[[str, float], None]) -> None:
        self._config = config
        self._on_trip = on_trip
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()
        self._tripped = False

    @property
    def tripped(self) -> bool:
        return self._tripped

    def start(self) -> None:
        """Start (or restart) the watchdog timer."""
        with self._lock:
            self._cancel_timer()
            self._tripped = False
            self._arm()

    def feed(self) -> None:
        """Reset the watchdog timer (signal progress)."""
        with self._lock:
            if not self._tripped:
                self._cancel_timer()
                self._arm()

    def stop(self) -> None:
        """Stop the watchdog without tripping."""
        with self._lock:
            self._cancel_timer()

    def _arm(self) -> None:
        self._timer = threading.Timer(
            self._config.stall_timeout, self._trip
        )
        self._timer.daemon = True
        self._timer.start()

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def _trip(self) -> None:
        with self._lock:
            self._tripped = True
        self._on_trip(self._config.key, self._config.stall_timeout)
