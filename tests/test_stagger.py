"""Tests for retryctl.stagger and retryctl.stagger_hook."""
from __future__ import annotations

import pytest

from retryctl.stagger import (
    StaggerConfig,
    StaggerState,
    StaggerViolation,
    apply_stagger,
)
from retryctl.stagger_hook import attach_stagger_hooks
from retryctl.hooks import HookRegistry


# ---------------------------------------------------------------------------
# StaggerConfig
# ---------------------------------------------------------------------------

class TestStaggerConfig:
    def test_valid_config_accepted(self):
        cfg = StaggerConfig(window=1.0, key="svc")
        assert cfg.window == 1.0
        assert cfg.key == "svc"

    def test_zero_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            StaggerConfig(window=0.0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window"):
            StaggerConfig(window=-0.5)

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            StaggerConfig(window=1.0, key="   ")

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key"):
            StaggerConfig(window=1.0, key="")


# ---------------------------------------------------------------------------
# StaggerState
# ---------------------------------------------------------------------------

def _make_state(window: float = 2.0, seed: int = 42) -> StaggerState:
    return StaggerState(config=StaggerConfig(window=window, seed=seed))


class TestStaggerState:
    def test_offset_within_window(self):
        state = _make_state(window=5.0)
        for _ in range(20):
            offset = state.next_offset()
            assert 0.0 <= offset < 5.0

    def test_deterministic_with_seed(self):
        s1 = _make_state(seed=7)
        s2 = _make_state(seed=7)
        assert [s1.next_offset() for _ in range(5)] == [s2.next_offset() for _ in range(5)]

    def test_key_forwarded(self):
        state = _make_state()
        assert state.key == "default"


# ---------------------------------------------------------------------------
# StaggerViolation
# ---------------------------------------------------------------------------

class TestStaggerViolation:
    def test_message_contains_key_and_offset(self):
        exc = StaggerViolation(key="grp", offset=0.123)
        assert "grp" in str(exc)
        assert "0.123" in str(exc)


# ---------------------------------------------------------------------------
# apply_stagger
# ---------------------------------------------------------------------------

class TestApplyStagger:
    def test_calls_sleep_with_offset(self):
        slept: list[float] = []
        state = _make_state(window=1.0, seed=0)
        returned = apply_stagger(state, sleep_fn=slept.append)
        assert len(slept) == 1
        assert slept[0] == returned
        assert 0.0 <= returned < 1.0


# ---------------------------------------------------------------------------
# attach_stagger_hooks
# ---------------------------------------------------------------------------

def _make_result():
    from retryctl.executor import ExecutionResult
    return ExecutionResult(succeeded=False, exit_code=1, stdout="", stderr="", attempts=1)


def _make_ctx():
    from retryctl.context import RetryContext
    return RetryContext(max_attempts=3)


class TestAttachStaggerHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.slept: list[float] = []
        self.state = _make_state(window=2.0, seed=1)
        attach_stagger_hooks(self.registry, self.state, sleep_fn=self.slept.append)

    def test_on_retry_applies_stagger(self):
        self.registry.fire_on_retry(_make_result(), _make_ctx())
        assert len(self.slept) == 1
        assert 0.0 <= self.slept[0] < 2.0

    def test_multiple_retries_each_staggered(self):
        for _ in range(3):
            self.registry.fire_on_retry(_make_result(), _make_ctx())
        assert len(self.slept) == 3
