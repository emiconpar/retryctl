"""Hook wiring for deadline enforcement."""
from __future__ import annotations

from retryctl.deadline import DeadlineState
from retryctl.hooks import HookRegistry


def attach_deadline_hooks(registry: HookRegistry, state: DeadlineState) -> None:
    """Register hooks that check the deadline before every retry attempt.

    The check fires:
    - *on_retry*: before sleeping and re-running the command, so we abort
      early if there is no time budget left.
    - *on_attempt_failure*: immediately after a failure is recorded, so we
      surface the deadline error without waiting for the next retry cycle.
    """
    registry.register_on_retry(_make_on_retry(state))
    registry.register_on_attempt_failure(_make_on_attempt_failure(state))


def _make_on_retry(state: DeadlineState):
    def _on_retry(result, ctx) -> None:  # noqa: ANN001
        state.check()

    return _on_retry


def _make_on_attempt_failure(state: DeadlineState):
    def _on_attempt_failure(result, ctx) -> None:  # noqa: ANN001
        state.check()

    return _on_attempt_failure
