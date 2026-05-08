"""Suppress specific exit codes from being treated as failures.

Allows certain exit codes to be silently accepted as successful outcomes,
preventing retries and reporting them as succeeded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Iterable


@dataclass(frozen=True)
class SuppressConfig:
    """Configuration for exit code suppression."""

    codes: FrozenSet[int] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        for code in self.codes:
            if not isinstance(code, int):
                raise TypeError(f"Suppressed codes must be integers, got {type(code)!r}")

    @classmethod
    def from_iterable(cls, codes: Iterable[int]) -> "SuppressConfig":
        """Build a SuppressConfig from any iterable of ints."""
        return cls(codes=frozenset(codes))


class SuppressedExit(Exception):
    """Raised internally when an exit code is suppressed."""

    def __init__(self, code: int) -> None:
        self.code = code
        super().__init__(f"Exit code {code} is suppressed")


def is_suppressed(config: SuppressConfig, exit_code: int) -> bool:
    """Return True if *exit_code* is in the suppressed set."""
    return exit_code in config.codes


def check_suppressed(config: SuppressConfig, exit_code: int) -> None:
    """Raise :class:`SuppressedExit` if *exit_code* is suppressed.

    This is a convenience helper for executor integration points that
    want to short-circuit retry logic for suppressed codes.
    """
    if is_suppressed(config, exit_code):
        raise SuppressedExit(exit_code)


def describe_suppressed(config: SuppressConfig) -> str:
    """Return a human-readable summary of the suppressed codes."""
    if not config.codes:
        return "no exit codes suppressed"
    sorted_codes = sorted(config.codes)
    codes_str = ", ".join(str(c) for c in sorted_codes)
    return f"suppressed exit codes: {codes_str}"
