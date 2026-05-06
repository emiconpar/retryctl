"""Reporters for surfacing correlation IDs after a run."""
from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from typing import IO

from retryctl.correlation import CorrelationContext


class CorrelationReporter(ABC):
    """Base class for correlation ID reporters."""

    @abstractmethod
    def report(self, ctx: CorrelationContext) -> None:
        """Emit correlation information."""


class NullCorrelationReporter(CorrelationReporter):
    """No-op reporter; useful as a default."""

    def report(self, ctx: CorrelationContext) -> None:  # noqa: D102
        pass


class TextCorrelationReporter(CorrelationReporter):
    """Writes a human-readable correlation ID line to a stream."""

    def __init__(self, stream: IO[str] = sys.stderr) -> None:
        self._stream = stream

    def report(self, ctx: CorrelationContext) -> None:  # noqa: D102
        self._stream.write(f"correlation_id={ctx.correlation_id}\n")


class JsonCorrelationReporter(CorrelationReporter):
    """Writes a JSON object containing the correlation ID to a stream."""

    def __init__(self, stream: IO[str] = sys.stderr) -> None:
        self._stream = stream

    def report(self, ctx: CorrelationContext) -> None:  # noqa: D102
        payload = {
            "correlation_id": ctx.correlation_id,
            "env_var": ctx.config.env_var,
        }
        self._stream.write(json.dumps(payload) + "\n")
