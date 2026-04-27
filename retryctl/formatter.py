"""Output formatting utilities for retryctl execution results."""

from __future__ import annotations

import json
from dataclasses import asdict
from enum import Enum
from typing import Any

from retryctl.executor import ExecutionResult


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    QUIET = "quiet"


def _result_to_dict(result: ExecutionResult) -> dict[str, Any]:
    """Convert an ExecutionResult to a plain dictionary."""
    return {
        "succeeded": result.succeeded,
        "exit_code": result.exit_code,
        "attempts": result.attempts,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "elapsed": round(result.elapsed, 4),
    }


def format_result(result: ExecutionResult, fmt: OutputFormat) -> str:
    """Return a formatted string representation of *result*."""
    if fmt == OutputFormat.QUIET:
        return ""

    if fmt == OutputFormat.JSON:
        return json.dumps(_result_to_dict(result), indent=2)

    # TEXT (default)
    status = "succeeded" if result.succeeded else "failed"
    lines = [
        f"Status   : {status}",
        f"Exit code: {result.exit_code}",
        f"Attempts : {result.attempts}",
        f"Elapsed  : {result.elapsed:.4f}s",
    ]
    if result.stdout:
        lines.append(f"Stdout   :\n{result.stdout.rstrip()}")
    if result.stderr:
        lines.append(f"Stderr   :\n{result.stderr.rstrip()}")
    return "\n".join(lines)
