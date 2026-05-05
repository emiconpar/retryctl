"""Reporters that surface dead-letter queue contents."""
from __future__ import annotations

import json
import sys
from typing import IO

from retryctl.deadletter import DeadLetterQueue


class DeadLetterReporter:
    """Base class for dead-letter reporters."""

    def report(self, queue: DeadLetterQueue) -> None:  # pragma: no cover
        raise NotImplementedError


class NullDeadLetterReporter(DeadLetterReporter):
    """No-op reporter used when dead-letter reporting is disabled."""

    def report(self, queue: DeadLetterQueue) -> None:
        pass


class JsonDeadLetterReporter(DeadLetterReporter):
    """Writes all dead-letter entries as a JSON array to *stream*."""

    def __init__(self, stream: IO[str] = sys.stdout) -> None:
        self._stream = stream

    def report(self, queue: DeadLetterQueue) -> None:
        entries = [e.to_dict() for e in queue.all()]
        json.dump(entries, self._stream, indent=2)
        self._stream.write("\n")


class TextDeadLetterReporter(DeadLetterReporter):
    """Writes a human-readable summary of dead-letter entries to *stream*."""

    def __init__(self, stream: IO[str] = sys.stdout) -> None:
        self._stream = stream

    def report(self, queue: DeadLetterQueue) -> None:
        entries = queue.all()
        if not entries:
            self._stream.write("Dead-letter queue is empty.\n")
            return
        self._stream.write(f"Dead-letter entries: {len(entries)}\n")
        for i, entry in enumerate(entries, 1):
            cmd = " ".join(entry.command)
            self._stream.write(
                f"  [{i}] cmd={cmd!r} exit_code={entry.exit_code}"
                f" attempts={entry.attempts}\n"
            )
