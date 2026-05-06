"""Hook integration that applies redaction to attempt results before reporting."""
from __future__ import annotations

from typing import Optional

from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult
from retryctl.redact import Redactor


def attach_redact_hooks(registry: HookRegistry, redactor: Redactor) -> None:
    """Register hooks that redact stdout/stderr on every attempt outcome."""
    registry.register_on_attempt_failure(_make_handler(redactor))
    registry.register_on_retry(_make_handler(redactor))
    registry.register_on_final_failure(_make_handler(redactor))
    registry.register_on_success(_make_handler(redactor))


def _make_handler(redactor: Redactor):
    def _handler(result: ExecutionResult, ctx: HookContext) -> None:
        _redact_result(result, redactor)

    return _handler


def _redact_result(result: ExecutionResult, redactor: Redactor) -> None:
    """Mutate *result* in-place, replacing sensitive content."""
    if result.stdout is not None:
        object.__setattr__(result, "stdout", redactor.redact(result.stdout))
    if result.stderr is not None:
        object.__setattr__(result, "stderr", redactor.redact(result.stderr))
