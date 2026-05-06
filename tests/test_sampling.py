"""Tests for retryctl.sampling and retryctl.sampling_hook."""
from __future__ import annotations

import pytest

from retryctl.sampling import RetrySampler, SamplingConfig, SamplingSkipped
from retryctl.sampling_hook import attach_sampling_hooks
from retryctl.hooks import HookRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_sampler(rate: float, seed: int = 0) -> RetrySampler:
    return RetrySampler(SamplingConfig(rate=rate, seed=seed))


# ---------------------------------------------------------------------------
# SamplingConfig validation
# ---------------------------------------------------------------------------

class TestSamplingConfig:
    def test_valid_rate_accepted(self):
        cfg = SamplingConfig(rate=0.5)
        assert cfg.rate == 0.5

    def test_zero_rate_accepted(self):
        cfg = SamplingConfig(rate=0.0)
        assert cfg.rate == 0.0

    def test_one_rate_accepted(self):
        cfg = SamplingConfig(rate=1.0)
        assert cfg.rate == 1.0

    def test_negative_rate_raises(self):
        with pytest.raises(ValueError, match="rate must be in"):
            SamplingConfig(rate=-0.1)

    def test_rate_above_one_raises(self):
        with pytest.raises(ValueError, match="rate must be in"):
            SamplingConfig(rate=1.1)


# ---------------------------------------------------------------------------
# RetrySampler behaviour
# ---------------------------------------------------------------------------

class TestRetrySamplerAlwaysRetry:
    def setup_method(self):
        self.sampler = _make_sampler(rate=1.0)

    def test_should_retry_true(self):
        assert self.sampler.should_retry() is True

    def test_check_does_not_raise(self):
        self.sampler.check()  # must not raise


class TestRetrySamplerNeverRetry:
    def setup_method(self):
        self.sampler = _make_sampler(rate=0.0)

    def test_should_retry_false(self):
        assert self.sampler.should_retry() is False

    def test_check_raises_sampling_skipped(self):
        with pytest.raises(SamplingSkipped) as exc_info:
            self.sampler.check()
        assert exc_info.value.rate == 0.0

    def test_sampling_skipped_message(self):
        with pytest.raises(SamplingSkipped, match="retry suppressed"):
            self.sampler.check()


class TestRetrySamplerRate:
    def test_rate_property(self):
        sampler = _make_sampler(rate=0.7)
        assert sampler.rate == 0.7

    def test_deterministic_with_seed(self):
        s1 = _make_sampler(rate=0.5, seed=42)
        s2 = _make_sampler(rate=0.5, seed=42)
        results1 = [s1.should_retry() for _ in range(20)]
        results2 = [s2.should_retry() for _ in range(20)]
        assert results1 == results2


# ---------------------------------------------------------------------------
# sampling_hook integration
# ---------------------------------------------------------------------------

class TestAttachSamplingHooks:
    def setup_method(self):
        self.registry = HookRegistry()

    def test_on_retry_hook_registered(self):
        sampler = _make_sampler(rate=1.0)
        attach_sampling_hooks(self.registry, sampler)
        assert len(self.registry._on_retry) == 1

    def test_hook_passes_when_rate_is_one(self):
        sampler = _make_sampler(rate=1.0)
        attach_sampling_hooks(self.registry, sampler)
        # Should not raise
        for hook in self.registry._on_retry:
            hook(None, None)

    def test_hook_raises_when_rate_is_zero(self):
        sampler = _make_sampler(rate=0.0)
        attach_sampling_hooks(self.registry, sampler)
        with pytest.raises(SamplingSkipped):
            for hook in self.registry._on_retry:
                hook(None, None)
