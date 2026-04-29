"""Reporters that emit RunMetrics to various sinks."""
from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from typing import IO

from retryctl.metrics import RunMetrics


class MetricsReporter(ABC):
    """Abstract base for metrics reporters."""

    @abstractmethod
    def report(self, metrics: RunMetrics) -> None:
        """Emit metrics to the configured sink."""


class NullReporter(MetricsReporter):
    """No-op reporter used when metrics output is disabled."""

    def report(self, metrics: RunMetrics) -> None:  # noqa: D102
        pass


class JsonReporter(MetricsReporter):
    """Writes metrics as a single JSON object to a stream."""

    def __init__(self, stream: IO[str] = sys.stderr) -> None:
        self._stream = stream

    def report(self, metrics: RunMetrics) -> None:  # noqa: D102
        self._stream.write(json.dumps(metrics.to_dict(), indent=2))
        self._stream.write("\n")


class TextReporter(MetricsReporter):
    """Writes a human-readable metrics summary to a stream."""

    def __init__(self, stream: IO[str] = sys.stderr) -> None:
        self._stream = stream

    def report(self, metrics: RunMetrics) -> None:  # noqa: D102
        status = "succeeded" if metrics.succeeded else "failed"
        lines = [
            f"[retryctl] Run {status} after {metrics.total_attempts} attempt(s)",
            f"  command          : {' '.join(metrics.command)}",
            f"  final exit code  : {metrics.final_exit_code}",
            f"  total duration   : {metrics.total_duration_seconds:.3f}s",
            f"  total retry delay: {metrics.total_delay_seconds:.3f}s",
        ]
        for record in metrics.attempts:
            delay_str = (
                f", delay_after={record.delay_before_next:.2f}s"
                if record.delay_before_next is not None
                else ""
            )
            lines.append(
                f"  attempt #{record.attempt_number}: exit={record.exit_code} "
                f"duration={record.duration_seconds:.3f}s{delay_str}"
            )
        self._stream.write("\n".join(lines) + "\n")


def build_reporter(fmt: str, stream: IO[str] = sys.stderr) -> MetricsReporter:
    """Factory: return a reporter for the given format string."""
    if fmt == "json":
        return JsonReporter(stream)
    if fmt == "text":
        return TextReporter(stream)
    if fmt in ("none", "", None):
        return NullReporter()
    raise ValueError(f"Unknown metrics format: {fmt!r}")
