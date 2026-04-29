"""Audit log: structured per-attempt event records for retryctl."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional, TextIO
import sys


@dataclass
class AuditEvent:
    timestamp: float
    attempt: int
    exit_code: Optional[int]
    succeeded: bool
    delay_before_next: Optional[float] = None
    signal: Optional[str] = None
    note: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class AuditLog:
    command: List[str]
    events: List[AuditEvent] = field(default_factory=list)
    _start: float = field(default_factory=time.monotonic, repr=False)

    def record(self, event: AuditEvent) -> None:
        self.events.append(event)

    def write(self, stream: TextIO = sys.stderr) -> None:
        payload = {
            "command": self.command,
            "events": [e.to_dict() for e in self.events],
        }
        stream.write(json.dumps(payload) + "\n")


def make_audit_event(
    attempt: int,
    exit_code: Optional[int],
    succeeded: bool,
    delay_before_next: Optional[float] = None,
    signal: Optional[str] = None,
    note: Optional[str] = None,
) -> AuditEvent:
    return AuditEvent(
        timestamp=time.time(),
        attempt=attempt,
        exit_code=exit_code,
        succeeded=succeeded,
        delay_before_next=delay_before_next,
        signal=signal,
        note=note,
    )
