"""Command executor with retry logic and backoff."""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional, TYPE_CHECKING

from retryctl.backoff import BackoffStrategy, BackoffConfig

if TYPE_CHECKING:
    from retryctl.hooks import HookRegistry


@dataclass
class ExecutionResult:
    succeeded: bool
    exit_code: int
    stdout: str
    stderr: str
    attempts: int
    total_wait: float


@dataclass
class RetryConfig:
    max_attempts: int = 3
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff: BackoffConfig = field(default_factory=BackoffConfig)
    retry_on_codes: List[int] = field(default_factory=list)
    retry_on_any_error: bool = True


class CommandExecutor:
    def __init__(
        self,
        command: List[str],
        config: RetryConfig,
        hooks: Optional["HookRegistry"] = None,
    ) -> None:
        self._command = command
        self._config = config
        self._hooks = hooks

    def run(self) -> ExecutionResult:
        from retryctl.backoff import BackoffStrategy as BS
        from retryctl.backoff import BackoffConfig
        from retryctl.hooks import HookContext

        cfg = self._config
        bc = cfg.backoff

        # Import here to avoid circular at module level
        from retryctl.backoff import BackoffStrategy

        delay = bc.initial_delay
        total_wait = 0.0
        last_result: Optional[ExecutionResult] = None

        for attempt in range(1, cfg.max_attempts + 1):
            proc = subprocess.run(
                self._command,
                capture_output=True,
                text=True,
            )
            exit_code = proc.returncode
            succeeded = exit_code == 0

            last_result = ExecutionResult(
                succeeded=succeeded,
                exit_code=exit_code,
                stdout=proc.stdout,
                stderr=proc.stderr,
                attempts=attempt,
                total_wait=total_wait,
            )

            if succeeded:
                if self._hooks:
                    from retryctl.hooks import HookContext
                    self._hooks.fire_success(HookContext(attempt=attempt, result=last_result))
                return last_result

            should_retry = (
                cfg.retry_on_any_error
                or (exit_code in cfg.retry_on_codes)
            )

            if not should_retry or attempt == cfg.max_attempts:
                if self._hooks:
                    from retryctl.hooks import HookContext
                    self._hooks.fire_attempt_failure(
                        HookContext(attempt=attempt, result=last_result, next_delay=None)
                    )
                    self._hooks.fire_final_failure(
                        HookContext(attempt=attempt, result=last_result, next_delay=None)
                    )
                return last_result

            # Compute next delay
            if cfg.strategy == BackoffStrategy.FIXED:
                next_d = bc.initial_delay
            elif cfg.strategy == BackoffStrategy.LINEAR:
                next_d = bc.initial_delay * attempt
            else:  # EXPONENTIAL
                next_d = bc.initial_delay * (bc.multiplier ** (attempt - 1))
            next_d = min(next_d, bc.max_delay)

            if self._hooks:
                from retryctl.hooks import HookContext
                ctx = HookContext(attempt=attempt, result=last_result, next_delay=next_d)
                self._hooks.fire_attempt_failure(ctx)
                self._hooks.fire_retry(ctx)

            time.sleep(next_d)
            total_wait += next_d
            delay = next_d

        return last_result  # type: ignore[return-value]
