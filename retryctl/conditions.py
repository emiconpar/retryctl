"""Retry condition evaluators for retryctl."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Container, Optional

from retryctl.signals import exit_code_from_returncode, should_retry_on_signal


@dataclass
class RetryCondition:
    """Determines whether a failed attempt should be retried."""

    retry_on_codes: Container[int] = field(default_factory=lambda: [])
    retry_on_any_error: bool = False
    never_retry_on_signals: bool = True

    def should_retry(self, returncode: int) -> bool:
        """Return True if the given returncode warrants a retry.

        Args:
            returncode: The raw return code from subprocess (may be negative
                        for signal-terminated processes).

        Returns:
            True if the command should be retried, False otherwise.
        """
        if returncode == 0:
            return False

        # Negative return codes indicate signal termination on Unix.
        if returncode < 0:
            if self.never_retry_on_signals and not should_retry_on_signal(-returncode):
                return False
            # Treat signal-terminated processes as retriable only when
            # retry_on_any_error is set or the mapped exit code matches.
            exit_code = exit_code_from_returncode(returncode)
            return self.retry_on_any_error or exit_code in self.retry_on_codes

        if self.retry_on_any_error:
            return True

        return returncode in self.retry_on_codes

    def describe(self) -> str:
        """Return a human-readable summary of this retry condition.

        Useful for logging and debugging to understand what policy is active.

        Returns:
            A short string describing the active retry policy.
        """
        if self.retry_on_any_error:
            policy = "retry on any error"
        elif self.retry_on_codes:
            policy = f"retry on exit codes {sorted(self.retry_on_codes)}"
        else:
            policy = "no retry"

        signal_policy = "ignore signals" if self.never_retry_on_signals else "allow signal retries"
        return f"{policy}, {signal_policy}"


def build_condition(
    retry_on_codes: Optional[list[int]] = None,
    retry_on_any_error: bool = False,
    never_retry_on_signals: bool = True,
) -> RetryCondition:
    """Factory helper used by the runner and CLI layers."""
    codes: list[int] = retry_on_codes if retry_on_codes is not None else []
    return RetryCondition(
        retry_on_codes=codes,
        retry_on_any_error=retry_on_any_error,
        never_retry_on_signals=never_retry_on_signals,
    )
