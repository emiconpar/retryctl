"""Hook integration for ramp-up state tracking."""
from __future__ import annotations

from retryctl.hooks import HookRegistry
from retryctl.rampup import RampUpState


def attach_rampup_hooks(registry: HookRegistry, state: RampUpState) -> None:
    """Register hooks that enforce ramp-up limits on each retry attempt."""

    def _on_retry(result, ctx) -> None:  # noqa: ANN001
        state.check()

    def _on_success(result, ctx) -> None:  # noqa: ANN001
        state.reset()

    registry.register_on_retry(_on_retry)
    registry.register_on_success(_on_success)
