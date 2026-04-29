"""Hook integration for rate limiting — wires the limiter into the HookRegistry."""

from __future__ import annotations

from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult
from retryctl.ratelimit import SlidingWindowRateLimiter, RateLimitExceeded


def attach_ratelimit_hooks(
    registry: HookRegistry,
    limiter: SlidingWindowRateLimiter,
) -> None:
    """Register hooks that enforce the rate limiter around each attempt."""

    registry.register_on_retry(_make_on_retry(limiter))


def _make_on_retry(
    limiter: SlidingWindowRateLimiter,
) -> "Callable[[ExecutionResult, HookContext], None]":
    def _on_retry(result: ExecutionResult, ctx: HookContext) -> None:
        """Called before each retry; raises if the rate limit would be exceeded."""
        limiter.check_and_record()

    return _on_retry
