"""Dry-run support: simulate retry execution without running the real command."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DryRunConfig:
    """Configuration for dry-run mode."""

    enabled: bool = False
    simulated_exit_code: int = 0
    simulated_stdout: str = ""
    simulated_stderr: str = ""
    verbose: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not isinstance(self.simulated_exit_code, int):
            raise TypeError("simulated_exit_code must be an int")


@dataclass
class DryRunRecord:
    """A record of a single simulated attempt."""

    attempt: int
    command: List[str]
    simulated_exit_code: int
    note: str = "dry-run: command not executed"

    def to_dict(self) -> dict:
        return {
            "attempt": self.attempt,
            "command": self.command,
            "simulated_exit_code": self.simulated_exit_code,
            "note": self.note,
        }


@dataclass
class DryRunLog:
    """Accumulates records of all simulated attempts."""

    records: List[DryRunRecord] = field(default_factory=list)

    def record(self, attempt: int, command: List[str], exit_code: int) -> DryRunRecord:
        entry = DryRunRecord(
            attempt=attempt,
            command=command,
            simulated_exit_code=exit_code,
        )
        self.records.append(entry)
        return entry

    def all_records(self) -> List[DryRunRecord]:
        return list(self.records)

    def summary(self) -> str:
        lines = [f"dry-run summary: {len(self.records)} simulated attempt(s)"]
        for r in self.records:
            lines.append(
                f"  attempt {r.attempt}: command={r.command!r} exit_code={r.simulated_exit_code}"
            )
        return "\n".join(lines)
