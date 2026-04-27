"""Signal handling for retryctl — captures OS signals during command execution
and translates them into structured exit information."""

from __future__ import annotations

import signal
from dataclasses import dataclass, field
from typing import Optional, Set


# Signals that indicate the child process was terminated by a signal
_FATAL_SIGNALS: Set[int] = {
    signal.SIGTERM,
    signal.SIGINT,
    signal.SIGHUP,
    signal.SIGKILL,
}


@dataclass
class SignalInfo:
    """Structured information about a signal that terminated a process."""

    signum: int
    name: str
    is_fatal: bool

    @classmethod
    def from_signum(cls, signum: int) -> "SignalInfo":
        try:
            sig = signal.Signals(signum)
            name = sig.name
        except ValueError:
            name = f"SIG{signum}"
        return cls(
            signum=signum,
            name=name,
            is_fatal=signum in _FATAL_SIGNALS,
        )


def exit_code_from_returncode(returncode: int) -> tuple[int, Optional[SignalInfo]]:
    """Convert a subprocess returncode to an exit code and optional SignalInfo.

    On POSIX systems, if a process is killed by a signal, subprocess returns
    a negative value equal to -signum.

    Returns:
        (exit_code, signal_info) where signal_info is None if the process
        exited normally.
    """
    if returncode < 0:
        signum = -returncode
        sig_info = SignalInfo.from_signum(signum)
        # Mimic shell convention: 128 + signum
        exit_code = 128 + signum
        return exit_code, sig_info
    return returncode, None


def should_retry_on_signal(sig_info: Optional[SignalInfo], retry_on_signals: bool) -> bool:
    """Determine whether a signal-terminated process should be retried."""
    if sig_info is None:
        return False
    if sig_info.is_fatal:
        return False
    return retry_on_signals
