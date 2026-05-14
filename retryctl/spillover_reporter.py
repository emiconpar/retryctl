"""Reporters for spillover results."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Optional

from retryctl.spillover import SpilloverResult


class SpilloverReporter(ABC):
    @abstractmethod
    def report(self, result: SpilloverResult) -> None:  # pragma: no cover
        ...


class NullSpilloverReporter(SpilloverReporter):
    def report(self, result: SpilloverResult) -> None:
        pass


class TextSpilloverReporter(SpilloverReporter):
    def __init__(self, file=None) -> None:
        import sys
        self._file = file or sys.stderr

    def report(self, result: SpilloverResult) -> None:
        status = "ok" if result.exit_code == 0 else "failed"
        cmd = " ".join(result.command)
        self._file.write(
            f"[spillover] command={cmd!r} attempt={result.attempt} "
            f"exit_code={result.exit_code} status={status}\n"
        )


class JsonSpilloverReporter(SpilloverReporter):
    def __init__(self, file=None) -> None:
        import sys
        self._file = file or sys.stderr

    def report(self, result: SpilloverResult) -> None:
        self._file.write(json.dumps(result.to_dict()) + "\n")
