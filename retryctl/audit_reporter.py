"""Write the audit log to a file or stderr at the end of a run."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from retryctl.audit import AuditLog


class AuditReporter:
    """Writes an AuditLog to a destination after a run completes."""

    def __init__(self, log: AuditLog, path: Optional[str] = None) -> None:
        self._log = log
        self._path = Path(path) if path else None

    def report(self) -> None:
        if self._path is not None:
            with self._path.open("a", encoding="utf-8") as fh:
                self._log.write(stream=fh)
        else:
            self._log.write(stream=sys.stderr)


class NullAuditReporter:
    """No-op reporter used when audit logging is disabled."""

    def report(self) -> None:  # pragma: no cover
        pass


def build_audit_reporter(
    command: list[str],
    enabled: bool = False,
    path: Optional[str] = None,
) -> tuple["AuditLog | None", "AuditReporter | NullAuditReporter"]:
    """Factory: returns (log, reporter) pair.

    When *enabled* is False both values are None / NullAuditReporter so callers
    do not need to branch on audit being configured.
    """
    if not enabled:
        return None, NullAuditReporter()
    log = AuditLog(command=command)
    reporter = AuditReporter(log=log, path=path)
    return log, reporter
