"""Metrics collection for retry execution runs."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class AttemptRecord:
    """Record of a single command attempt."""
    attempt_number: int
    exit_code: int
    duration_seconds: float
    delay_before_next: Optional[float] = None  # None if this was the final attempt


@dataclass
class RunMetrics:
    """Aggregated metrics for a full retry run."""
    command: List[str]
    attempts: List[AttemptRecord] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    succeeded: bool = False
    final_exit_code: int = 0
    _start_time: float = field(default_factory=time.monotonic, repr=False)

    def record_attempt(
        self,
        attempt_number: int,
        exit_code: int,
        duration: float,
        delay_before_next: Optional[float] = None,
    ) -> None:
        self.attempts.append(
            AttemptRecord(
                attempt_number=attempt_number,
                exit_code=exit_code,
                duration_seconds=duration,
                delay_before_next=delay_before_next,
            )
        )

    def finish(self, succeeded: bool, final_exit_code: int) -> None:
        self.succeeded = succeeded
        self.final_exit_code = final_exit_code
        self.total_duration_seconds = time.monotonic() - self._start_time

    @property
    def total_attempts(self) -> int:
        return len(self.attempts)

    @property
    def total_delay_seconds(self) -> float:
        return sum(a.delay_before_next for a in self.attempts if a.delay_before_next)

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "succeeded": self.succeeded,
            "final_exit_code": self.final_exit_code,
            "total_attempts": self.total_attempts,
            "total_duration_seconds": round(self.total_duration_seconds, 4),
            "total_delay_seconds": round(self.total_delay_seconds, 4),
            "attempts": [
                {
                    "attempt_number": a.attempt_number,
                    "exit_code": a.exit_code,
                    "duration_seconds": round(a.duration_seconds, 4),
                    "delay_before_next": a.delay_before_next,
                }
                for a in self.attempts
            ],
        }
