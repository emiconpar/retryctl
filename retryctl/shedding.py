"""Load shedding support: drop retries when system load exceeds a threshold."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional


class LoadSheddingTripped(Exception):
    """Raised when load shedding drops a retry attempt."""

    def __init__(self, current_load: float, threshold: float) -> None:
        self.current_load = current_load
        self.threshold = threshold
        super().__init__(
            f"Load shedding active: load {current_load:.2f} exceeds threshold {threshold:.2f}"
        )


@dataclass
class SheddingConfig:
    """Configuration for load-based retry shedding."""

    threshold: float
    load_source: str = "cpu"  # "cpu" or "loadavg"
    min_attempt: int = 1  # only shed retries at or after this attempt number

    def __post_init__(self) -> None:
        if self.threshold <= 0.0:
            raise ValueError("threshold must be positive")
        if self.threshold > 1.0 and self.load_source == "cpu":
            raise ValueError("cpu threshold must be in (0.0, 1.0]")
        if self.load_source not in ("cpu", "loadavg"):
            raise ValueError("load_source must be 'cpu' or 'loadavg'")
        if self.min_attempt < 1:
            raise ValueError("min_attempt must be >= 1")


def _read_cpu_load() -> float:
    """Return a rough CPU utilisation fraction using /proc/stat if available."""
    try:
        with open("/proc/stat") as fh:
            line = fh.readline()
        parts = line.split()
        # user, nice, system, idle, iowait, irq, softirq
        values = [int(p) for p in parts[1:8]]
        idle = values[3]
        total = sum(values)
        return 1.0 - (idle / total) if total else 0.0
    except OSError:
        return 0.0


def _read_loadavg() -> float:
    """Return the 1-minute load average."""
    try:
        return os.getloadavg()[0]
    except (OSError, AttributeError):
        return 0.0


@dataclass
class SheddingState:
    config: SheddingConfig
    _shed_count: int = field(default=0, init=False)

    def check(self, attempt_number: int) -> None:
        """Raise LoadSheddingTripped if current load exceeds the threshold."""
        if attempt_number < self.config.min_attempt:
            return
        if self.config.load_source == "cpu":
            current = _read_cpu_load()
        else:
            current = _read_loadavg()
        if current > self.config.threshold:
            self._shed_count += 1
            raise LoadSheddingTripped(current, self.config.threshold)

    @property
    def shed_count(self) -> int:
        return self._shed_count
