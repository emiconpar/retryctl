"""Lifecycle hooks for retry events."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from retryctl.executor import ExecutionResult


@dataclass
class HookContext:
    """Context passed to each lifecycle hook."""

    attempt: int
    result: ExecutionResult
    next_delay: Optional[float] = None  # None on final attempt


# Hook signature: receives a HookContext, returns nothing.
HookFn = Callable[[HookContext], None]


@dataclass
class HookRegistry:
    """Holds collections of hooks for each retry lifecycle event."""

    on_attempt_failure: List[HookFn] = field(default_factory=list)
    on_retry: List[HookFn] = field(default_factory=list)
    on_final_failure: List[HookFn] = field(default_factory=list)
    on_success: List[HookFn] = field(default_factory=list)

    def register_on_attempt_failure(self, fn: HookFn) -> None:
        self.on_attempt_failure.append(fn)

    def register_on_retry(self, fn: HookFn) -> None:
        self.on_retry.append(fn)

    def register_on_final_failure(self, fn: HookFn) -> None:
        self.on_final_failure.append(fn)

    def register_on_success(self, fn: HookFn) -> None:
        self.on_success.append(fn)

    def fire_attempt_failure(self, ctx: HookContext) -> None:
        for fn in self.on_attempt_failure:
            fn(ctx)

    def fire_retry(self, ctx: HookContext) -> None:
        for fn in self.on_retry:
            fn(ctx)

    def fire_final_failure(self, ctx: HookContext) -> None:
        for fn in self.on_final_failure:
            fn(ctx)

    def fire_success(self, ctx: HookContext) -> None:
        for fn in self.on_success:
            fn(ctx)


def build_logging_hooks(verbose: bool = False) -> HookRegistry:
    """Return a HookRegistry pre-populated with stderr logging hooks."""
    import sys

    registry = HookRegistry()

    def _on_failure(ctx: HookContext) -> None:
        print(
            f"[retryctl] attempt {ctx.attempt} failed with exit code "
            f"{ctx.result.exit_code}",
            file=sys.stderr,
        )

    def _on_retry(ctx: HookContext) -> None:
        print(
            f"[retryctl] retrying in {ctx.next_delay:.2f}s "
            f"(attempt {ctx.attempt})",
            file=sys.stderr,
        )

    def _on_final_failure(ctx: HookContext) -> None:
        print(
            f"[retryctl] all attempts exhausted after attempt {ctx.attempt}",
            file=sys.stderr,
        )

    def _on_success(ctx: HookContext) -> None:
        if verbose:
            print(
                f"[retryctl] succeeded on attempt {ctx.attempt}",
                file=sys.stderr,
            )

    registry.register_on_attempt_failure(_on_failure)
    registry.register_on_retry(_on_retry)
    registry.register_on_final_failure(_on_final_failure)
    registry.register_on_success(_on_success)
    return registry
