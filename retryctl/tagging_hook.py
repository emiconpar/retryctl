"""Hook integration for attempt tagging."""
from __future__ import annotations

from retryctl.hooks import HookRegistry
from retryctl.tagging import TaggingConfig, build_tags

_TAG_KEY = "attempt_tags"


def attach_tagging_hooks(registry: HookRegistry, config: TaggingConfig) -> None:
    """Register hooks that annotate HookContext.extra with attempt tags."""

    def _on_attempt_failure(result, ctx) -> None:  # type: ignore[no-untyped-def]
        tags = build_tags(
            config,
            attempt_number=ctx.attempt,
            exit_code=result.exit_code,
        )
        ctx.extra[_TAG_KEY] = tags

    def _on_retry(result, ctx) -> None:  # type: ignore[no-untyped-def]
        if _TAG_KEY not in ctx.extra:
            tags = build_tags(
                config,
                attempt_number=ctx.attempt,
                exit_code=result.exit_code,
            )
            ctx.extra[_TAG_KEY] = tags

    def _on_final_failure(result, ctx) -> None:  # type: ignore[no-untyped-def]
        tags = build_tags(
            config,
            attempt_number=ctx.attempt,
            exit_code=result.exit_code,
        )
        ctx.extra[_TAG_KEY] = tags

    def _on_success(result, ctx) -> None:  # type: ignore[no-untyped-def]
        tags = build_tags(
            config,
            attempt_number=ctx.attempt,
            exit_code=result.exit_code,
        )
        ctx.extra[_TAG_KEY] = tags

    registry.register_on_attempt_failure(_on_attempt_failure)
    registry.register_on_retry(_on_retry)
    registry.register_on_final_failure(_on_final_failure)
    registry.register_on_success(_on_success)
