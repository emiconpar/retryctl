"""Tee output: capture stdout/stderr while also streaming to a secondary sink."""
from __future__ import annotations

import io
import sys
from dataclasses import dataclass, field
from typing import Callable, IO, Optional


@dataclass
class TeeConfig:
    """Configuration for tee output behaviour."""

    enabled: bool = True
    stream: str = "both"  # "stdout", "stderr", or "both"
    # Optional callable sink; defaults to writing to the real stdout/stderr.
    sink: Optional[Callable[[str, str], None]] = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("enabled must be a bool")
        valid_streams = {"stdout", "stderr", "both"}
        if self.stream not in valid_streams:
            raise ValueError(f"stream must be one of {valid_streams!r}")


@dataclass
class TeeRecord:
    """Record of what was teed during a single attempt."""

    attempt: int
    stdout_bytes: int = 0
    stderr_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "attempt": self.attempt,
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
        }


def apply_tee(
    config: TeeConfig,
    attempt: int,
    stdout: str,
    stderr: str,
    sink: Optional[Callable[[str, str], None]] = None,
) -> TeeRecord:
    """Write captured output to the configured sink and return a TeeRecord.

    Args:
        config:  Active TeeConfig.
        attempt: Current attempt number (1-based).
        stdout:  Captured stdout text.
        stderr:  Captured stderr text.
        sink:    Override sink; falls back to config.sink then real streams.
    """
    if not config.enabled:
        return TeeRecord(attempt=attempt)

    resolved_sink = sink or config.sink or _default_sink

    tee_stdout = config.stream in ("stdout", "both")
    tee_stderr = config.stream in ("stderr", "both")

    written_stdout = 0
    written_stderr = 0

    if tee_stdout and stdout:
        resolved_sink("stdout", stdout)
        written_stdout = len(stdout.encode())

    if tee_stderr and stderr:
        resolved_sink("stderr", stderr)
        written_stderr = len(stderr.encode())

    return TeeRecord(
        attempt=attempt,
        stdout_bytes=written_stdout,
        stderr_bytes=written_stderr,
    )


def _default_sink(stream: str, text: str) -> None:
    target: IO[str] = sys.stdout if stream == "stdout" else sys.stderr
    target.write(text)
    target.flush()
