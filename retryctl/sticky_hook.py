"""Hook integration for sticky retry."""
from __future__ import annotations

from retryctl.hooks import HookRegistry
from retryctl.sticky import StickyConfig, StickyState


def attach_sticky_hooks(
    registry: HookRegistry,
    config: StickyConfig,
    state: StickyState,
) -> None:
    """Register sticky-retry hooks on *registry*."""

    def _on_retry(result, ctx) -> None:  # type: ignore[no-untyped-def]
        key = config.key
        state.record_attempt(key)
        if state.should_fallback(key):
            # Signal that the caller should route to a different node.
            ctx.metadata["sticky_fallback"] = True
            ctx.metadata["sticky_key"] = key
        else:
            node = state.get_pinned_node(key)
            if node is not None:
                ctx.metadata["sticky_node"] = node
            ctx.metadata["sticky_fallback"] = False
            ctx.metadata["sticky_key"] = key

    def _on_success(result, ctx) -> None:  # type: ignore[no-untyped-def]
        state.clear(config.key)

    def _on_final_failure(result, ctx) -> None:  # type: ignore[no-untyped-def]
        state.clear(config.key)

    registry.register_on_retry(_on_retry)
    registry.register_on_success(_on_success)
    registry.register_on_final_failure(_on_final_failure)
