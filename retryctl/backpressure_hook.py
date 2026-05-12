"""Hook integration for backpressure enforcement."""
from __future__ import annotations

from retryctl.backpressure import BackpressureState
from retryctl.hooks import HookRegistry


def attach_backpressure_hooks(
    registry: HookRegistry,
    state: BackpressureState,
) -> None:
    """Register hooks so backpressure is checked before each retry.

    On attempt failure the hook reads the exit code as a crude pressure
    signal (non-zero == some load).  Callers may call ``state.update()``
    directly from application code for finer-grained control.
    """
    registry.register_on_retry(_make_on_retry(state))
    registry.register_on_attempt_failure(_make_on_attempt_failure(state))


def _make_on_retry(state: BackpressureState):
    def _on_retry(result, ctx) -> None:  # type: ignore[type-arg]
        state.check()

    return _on_retry


def _make_on_attempt_failure(state: BackpressureState):
    def _on_attempt_failure(result, ctx) -> None:  # type: ignore[type-arg]
        # Treat any non-zero exit as a small pressure bump (0.1 per failure),
        # capped at 1.0, so repeated failures accumulate backpressure.
        if result.exit_code != 0:
            new_pressure = min(1.0, state.current_pressure + 0.1)
            state.update(new_pressure)

    return _on_attempt_failure
