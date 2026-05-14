"""Spillover: redirect retries to an alternate command when primary exhausts attempts."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SpilloverConfig:
    command: List[str]
    max_attempts: int = 1
    timeout: Optional[float] = None
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError("spillover command must not be empty")
        if self.max_attempts < 1:
            raise ValueError("spillover max_attempts must be >= 1")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("spillover timeout must be positive")
        if not isinstance(self.enabled, bool):
            raise TypeError("spillover enabled must be a bool")


@dataclass
class SpilloverResult:
    command: List[str]
    exit_code: int
    stdout: str
    stderr: str
    attempt: int
    triggered: bool = True

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "attempt": self.attempt,
            "triggered": self.triggered,
        }


def run_spillover(config: SpilloverConfig) -> SpilloverResult:
    """Execute the spillover command, retrying up to config.max_attempts times."""
    last_result: Optional[SpilloverResult] = None
    for attempt in range(1, config.max_attempts + 1):
        try:
            proc = subprocess.run(
                config.command,
                capture_output=True,
                text=True,
                timeout=config.timeout,
            )
            last_result = SpilloverResult(
                command=config.command,
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                attempt=attempt,
            )
            if proc.returncode == 0:
                return last_result
        except subprocess.TimeoutExpired:
            last_result = SpilloverResult(
                command=config.command,
                exit_code=124,
                stdout="",
                stderr="spillover timed out",
                attempt=attempt,
            )
    assert last_result is not None
    return last_result
