"""Hook integration that attaches label metadata to audit events and metrics.

Calling :func:`attach_labels_hooks` registers hooks on a :class:`HookRegistry`
so that every attempt failure, retry, final failure, and success event is
decorated with the supplied :class:`LabelSet`.
"""
from __future__ import annotations

from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult
from retryctl.labels import LabelSet


def attach_labels_hooks(registry: HookRegistry, labels: LabelSet) -> None:
    """Register hooks that inject *labels* into the HookContext extra data.

    Labels are stored under the key ``"labels"`` in ``ctx.extra`` so that
    downstream hooks (e.g. audit, metrics) can read them.
    """
    if not labels.all():
        # Nothing to attach — avoid unnecessary overhead.
        return

    def _inject(ctx: HookContext, result: ExecutionResult) -> None:
        existing: LabelSet = ctx.extra.get("labels", LabelSet())
        ctx.extra["labels"] = existing.merge(labels)

    registry.register_on_attempt_failure(_inject)
    registry.register_on_retry(_inject)
    registry.register_on_final_failure(_inject)
    registry.register_on_success(_inject)
