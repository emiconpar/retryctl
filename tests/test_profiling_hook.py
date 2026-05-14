"""Tests for retryctl.profiling_hook."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult
from retryctl.profiling import ProfilingConfig, RunProfile
from retryctl.profiling_hook import attach_profiling_hooks


def _make_result() -> ExecutionResult:
    r = MagicMock(spec=ExecutionResult)
    r.exit_code = 1
    r.stdout = ""
    r.stderr = ""
    return r


def _make_ctx(attempt: int = 1, max_attempts: int = 3) -> HookContext:
    ctx = MagicMock(spec=HookContext)
    ctx.attempt = attempt
    ctx.max_attempts = max_attempts
    return ctx


class TestAttachProfilingHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.profile = RunProfile()
        self.config = ProfilingConfig(enabled=True, include_per_attempt=True)
        attach_profiling_hooks(self.registry, self.profile, self.config)

    def test_disabled_config_registers_no_hooks(self):
        registry = HookRegistry()
        profile = RunProfile()
        attach_profiling_hooks(registry, profile, ProfilingConfig(enabled=False))
        # fire success — nothing should break, no timings recorded
        result, ctx = _make_result(), _make_ctx()
        registry.fire_on_success(result, ctx)
        assert profile.attempt_timings == []

    def test_success_records_attempt_and_finishes_run(self):
        result, ctx = _make_result(), _make_ctx(attempt=1)
        self.registry.fire_on_success(result, ctx)
        assert len(self.profile.attempt_timings) == 1
        assert self.profile.total_duration is not None

    def test_final_failure_finishes_run(self):
        result, ctx = _make_result(), _make_ctx(attempt=3)
        self.registry.fire_on_final_failure(result, ctx)
        assert self.profile.total_duration is not None

    def test_attempt_failure_records_timing(self):
        result, ctx = _make_result(), _make_ctx(attempt=1)
        self.registry.fire_on_attempt_failure(result, ctx)
        assert len(self.profile.attempt_timings) == 1

    def test_multiple_attempts_accumulate(self):
        r, c1 = _make_result(), _make_ctx(attempt=1)
        c2 = _make_ctx(attempt=2)
        self.registry.fire_on_attempt_failure(r, c1)
        self.registry.fire_on_retry(r, c1)
        self.registry.fire_on_attempt_failure(r, c2)
        self.registry.fire_on_final_failure(r, c2)
        assert len(self.profile.attempt_timings) == 2

    def test_attempt_durations_are_positive(self):
        result, ctx = _make_result(), _make_ctx(attempt=1)
        time.sleep(0.01)
        self.registry.fire_on_success(result, ctx)
        for t in self.profile.attempt_timings:
            assert t.duration >= 0
