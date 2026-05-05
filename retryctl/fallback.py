"""Fallback command support: run an alternative command when all retries are exhausted."""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FallbackConfig:
    """Configuration for a fallback command executed on final failure."""

    command: List[str]
    timeout: Optional[float] = None
    capture_output: bool = True

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError("fallback command must not be empty")
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("fallback timeout must be positive")


@dataclass
class FallbackResult:
    """Result of executing a fallback command."""

    command: List[str]
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    ran: bool = True


def run_fallback(config: FallbackConfig) -> FallbackResult:
    """Execute the fallback command and return its result."""
    try:
        proc = subprocess.run(
            config.command,
            capture_output=config.capture_output,
            timeout=config.timeout,
            text=True,
        )
        return FallbackResult(
            command=config.command,
            exit_code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            ran=True,
        )
    except subprocess.TimeoutExpired:
        return FallbackResult(
            command=config.command,
            exit_code=124,
            stderr="fallback command timed out",
            ran=True,
        )
    except FileNotFoundError as exc:
        return FallbackResult(
            command=config.command,
            exit_code=127,
            stderr=f"fallback command not found: {exc}",
            ran=False,
        )
