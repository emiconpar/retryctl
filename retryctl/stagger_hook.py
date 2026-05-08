"""Hook integration for stagger: inject a random delay before each retry."""
from __future__ import annotations

from retryctl.hooks import HookRegistry
from retryctl.stagger import StaggerState, apply_stagger


def attach_stagger_hooks(
    registry: HookRegistry,
    state: StaggerState,
    sleep_fn=None,
) -> None:
    """Register stagger hooks on *registry*.

    A random offset within the configured window is injected before every
    retry attempt so that concurrent processes do not all wake at the same
    instant (thundering-herd mitigation).
    """
    registry.register_on_retry(_make_on_retry(state, sleep_fn))


def _make_on_retry(state: StaggerState, sleep_fn=None):
    def _on_retry(result, ctx) -> None:  # noqa: ANN001
        apply_stagger(state, sleep_fn=sleep_fn)

    return _on_retry
