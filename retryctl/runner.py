"""High-level runner that wires together CLI args, backoff, and executor."""

from typing import List, Optional

from retryctl.backoff import BackoffConfig, BackoffStrategy
from retryctl.executor import CommandExecutor, ExecutionResult, RetryConfig


def build_executor(
    strategy: str = "exponential",
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    multiplier: float = 2.0,
    jitter: bool = False,
    max_attempts: int = 3,
    retry_on_codes: Optional[List[int]] = None,
    stop_on_codes: Optional[List[int]] = None,
    timeout: Optional[float] = None,
) -> CommandExecutor:
    """Factory that builds a :class:`CommandExecutor` from plain parameters."""
    backoff_cfg = BackoffConfig(
        strategy=strategy,
        base_delay=base_delay,
        max_delay=max_delay,
        multiplier=multiplier,
        jitter=jitter,
    )
    backoff = BackoffStrategy(backoff_cfg)
    retry_cfg = RetryConfig(
        max_attempts=max_attempts,
        retry_on_codes=retry_on_codes or [],
        stop_on_codes=stop_on_codes or [],
        timeout=timeout,
    )
    return CommandExecutor(backoff=backoff, config=retry_cfg)


def run_command(
    command: List[str],
    **kwargs,
) -> ExecutionResult:
    """Convenience wrapper: build an executor and run *command*."""
    executor = build_executor(**kwargs)
    return executor.run(command)
