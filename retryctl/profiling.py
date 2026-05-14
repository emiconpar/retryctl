"""Profiling support: track per-attempt timing and aggregate run statistics."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ProfilingConfig:
    enabled: bool = True
    include_per_attempt: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not isinstance(self.include_per_attempt, bool):
            raise TypeError("include_per_attempt must be a bool")


@dataclass
class AttemptTiming:
    attempt: int
    started_at: float
    ended_at: float

    @property
    def duration(self) -> float:
        return self.ended_at - self.started_at

    def to_dict(self) -> dict:
        return {
            "attempt": self.attempt,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_s": round(self.duration, 6),
        }


@dataclass
class RunProfile:
    _timings: List[AttemptTiming] = field(default_factory=list)
    _run_start: Optional[float] = field(default=None)
    _run_end: Optional[float] = field(default=None)

    def start_run(self) -> None:
        self._run_start = time.monotonic()

    def finish_run(self) -> None:
        self._run_end = time.monotonic()

    def record_attempt(self, attempt: int, started_at: float, ended_at: float) -> None:
        self._timings.append(AttemptTiming(attempt, started_at, ended_at))

    @property
    def total_duration(self) -> Optional[float]:
        if self._run_start is None or self._run_end is None:
            return None
        return self._run_end - self._run_start

    @property
    def attempt_timings(self) -> List[AttemptTiming]:
        return list(self._timings)

    @property
    def average_attempt_duration(self) -> Optional[float]:
        if not self._timings:
            return None
        return sum(t.duration for t in self._timings) / len(self._timings)

    def to_dict(self, include_per_attempt: bool = True) -> dict:
        result: dict = {
            "total_duration_s": round(self.total_duration, 6) if self.total_duration is not None else None,
            "attempt_count": len(self._timings),
            "average_attempt_duration_s": round(self.average_attempt_duration, 6)
            if self.average_attempt_duration is not None
            else None,
        }
        if include_per_attempt:
            result["attempts"] = [t.to_dict() for t in self._timings]
        return result
