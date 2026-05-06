"""Hook integration for RetrySampler."""
from __future__ import annotations

from retryctl.hooks import HookRegistry
from retryctl.sampling import RetrySampler, SamplingSkipped


def attach_sampling_hooks(registry: HookRegistry, sampler: RetrySampler) -> None:
    """Register a pre-retry hook that enforces probabilistic sampling.

    When the sampler decides to suppress a retry, it raises
    :class:`SamplingSkipped`.  The executor is expected to treat this as a
    non-retriable terminal condition (similar to budget exhaustion).
    """
    registry.register_on_retry(_make_on_retry(sampler))


def _make_on_retry(sampler: RetrySampler):
    def _on_retry(ctx, result) -> None:  # noqa: ANN001
        sampler.check()

    return _on_retry
