"""Stealth mode: suppress retry-related output and headers on final success."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class StealthConfig:
    """Configuration for stealth mode output suppression."""

    enabled: bool = True
    suppress_headers: bool = True
    suppress_attempt_info: bool = True
    # Environment variable names whose values should be hidden in logs
    hidden_env_vars: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        if not isinstance(self.suppress_headers, bool):
            raise TypeError("suppress_headers must be a bool")
        if not isinstance(self.suppress_attempt_info, bool):
            raise TypeError("suppress_attempt_info must be a bool")
        if not isinstance(self.hidden_env_vars, list):
            raise TypeError("hidden_env_vars must be a list")
        for var in self.hidden_env_vars:
            if not isinstance(var, str) or not var.strip():
                raise ValueError(
                    f"hidden_env_vars entries must be non-blank strings, got {var!r}"
                )


@dataclass
class StealthRecord:
    """Records what was suppressed during a stealth run."""

    headers_suppressed: bool = False
    attempt_info_suppressed: bool = False
    hidden_vars_count: int = 0

    def to_dict(self) -> dict:
        return {
            "headers_suppressed": self.headers_suppressed,
            "attempt_info_suppressed": self.attempt_info_suppressed,
            "hidden_vars_count": self.hidden_vars_count,
        }


def apply_stealth(config: StealthConfig, output: str) -> tuple[str, StealthRecord]:
    """Apply stealth filtering to a block of output text.

    Returns the filtered output and a record of what was suppressed.
    """
    record = StealthRecord()

    if not config.enabled:
        return output, record

    lines = output.splitlines(keepends=True)
    filtered: List[str] = []

    for line in lines:
        if config.suppress_headers and line.startswith("[retryctl]"):
            record.headers_suppressed = True
            continue
        if config.suppress_attempt_info and "attempt" in line.lower() and "retryctl" in line.lower():
            record.attempt_info_suppressed = True
            continue
        filtered.append(line)

    result = "".join(filtered)

    if config.hidden_env_vars:
        record.hidden_vars_count = len(config.hidden_env_vars)

    return result, record
