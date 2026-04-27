"""Command executor with retry logic."""

import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional

from retryctl.backoff import BackoffStrategy


@dataclass
class ExecutionResult:
    """Result of a command execution attempt."""

    command: List[str]
    returncode: int
    attempts: int
    stdout: str = ""
    stderr: str = ""
    elapsed: float = 0.0
    succeeded: bool = False


@dataclass
class RetryConfig:
    """Configuration for retry behaviour."""

    max_attempts: int = 3
    retry_on_codes: List[int] = field(default_factory=lambda: [])
    stop_on_codes: List[int] = field(default_factory=lambda: [])
    timeout: Optional[float] = None


class CommandExecutor:
    """Executes shell commands with configurable retry and backoff."""

    def __init__(self, backoff: BackoffStrategy, config: RetryConfig) -> None:
        self.backoff = backoff
        self.config = config

    def run(self, command: List[str]) -> ExecutionResult:
        """Run *command*, retrying according to config and backoff strategy."""
        self.backoff.reset()
        start = time.monotonic()
        last_result: Optional[subprocess.CompletedProcess] = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                last_result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.config.timeout,
                )
            except subprocess.TimeoutExpired as exc:
                stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                return ExecutionResult(
                    command=command,
                    returncode=-1,
                    attempts=attempt,
                    stderr=stderr,
                    elapsed=time.monotonic() - start,
                    succeeded=False,
                )

            rc = last_result.returncode

            if rc == 0:
                return ExecutionResult(
                    command=command,
                    returncode=rc,
                    attempts=attempt,
                    stdout=last_result.stdout,
                    stderr=last_result.stderr,
                    elapsed=time.monotonic() - start,
                    succeeded=True,
                )

            if self.config.stop_on_codes and rc in self.config.stop_on_codes:
                break

            if self.config.retry_on_codes and rc not in self.config.retry_on_codes:
                break

            if attempt < self.config.max_attempts:
                delay = self.backoff.next_delay()
                time.sleep(delay)

        elapsed = time.monotonic() - start
        return ExecutionResult(
            command=command,
            returncode=last_result.returncode if last_result else -1,
            attempts=attempt,
            stdout=last_result.stdout if last_result else "",
            stderr=last_result.stderr if last_result else "",
            elapsed=elapsed,
            succeeded=False,
        )
