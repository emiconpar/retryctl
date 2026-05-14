"""Reporters for profiling data."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import IO

from retryctl.profiling import RunProfile, ProfilingConfig


class ProfilingReporter(ABC):
    @abstractmethod
    def report(self, profile: RunProfile, config: ProfilingConfig) -> None:
        ...


class NullProfilingReporter(ProfilingReporter):
    def report(self, profile: RunProfile, config: ProfilingConfig) -> None:
        return


class JsonProfilingReporter(ProfilingReporter):
    def __init__(self, stream: IO[str]) -> None:
        self._stream = stream

    def report(self, profile: RunProfile, config: ProfilingConfig) -> None:
        data = profile.to_dict(include_per_attempt=config.include_per_attempt)
        self._stream.write(json.dumps(data))
        self._stream.write("\n")


class TextProfilingReporter(ProfilingReporter):
    def __init__(self, stream: IO[str]) -> None:
        self._stream = stream

    def report(self, profile: RunProfile, config: ProfilingConfig) -> None:
        total = profile.total_duration
        avg = profile.average_attempt_duration
        self._stream.write(
            f"[profiling] total={total:.3f}s attempts={len(profile.attempt_timings)}"
            f" avg={avg:.3f}s\n"
            if total is not None and avg is not None
            else "[profiling] run not finished\n"
        )
        if config.include_per_attempt:
            for t in profile.attempt_timings:
                self._stream.write(
                    f"  attempt={t.attempt} duration={t.duration:.3f}s\n"
                )
