"""Tests for retryctl.sticky and retryctl.sticky_hook."""
from __future__ import annotations

import pytest

from retryctl.sticky import StickyConfig, StickyState
from retryctl.sticky_hook import attach_sticky_hooks
from retryctl.hooks import HookRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_state(max_same: int = 3, fallback: bool = True) -> StickyState:
    cfg = StickyConfig(key="host", max_same_node_attempts=max_same, fallback_on_exhaust=fallback)
    return StickyState(config=cfg)


class _FakeResult:
    pass


class _FakeCtx:
    def __init__(self):
        self.metadata: dict = {}


# ---------------------------------------------------------------------------
# StickyConfig validation
# ---------------------------------------------------------------------------

class TestStickyConfig:
    def test_valid_config_accepted(self):
        cfg = StickyConfig(key="node-1", max_same_node_attempts=2)
        assert cfg.key == "node-1"

    def test_blank_key_raises(self):
        with pytest.raises(ValueError, match="non-blank"):
            StickyConfig(key="   ")

    def test_empty_key_raises(self):
        with pytest.raises(ValueError):
            StickyConfig(key="")

    def test_zero_max_same_node_raises(self):
        with pytest.raises(ValueError, match=">= 1"):
            StickyConfig(key="x", max_same_node_attempts=0)

    def test_non_bool_fallback_raises(self):
        with pytest.raises(TypeError):
            StickyConfig(key="x", fallback_on_exhaust="yes")  # type: ignore


# ---------------------------------------------------------------------------
# StickyState behaviour
# ---------------------------------------------------------------------------

class TestStickyState:
    def test_pin_and_get(self):
        s = _make_state()
        s.pin("host", "node-42")
        assert s.get_pinned_node("host") == "node-42"

    def test_no_pin_returns_none(self):
        s = _make_state()
        assert s.get_pinned_node("host") is None

    def test_should_fallback_after_max_attempts(self):
        s = _make_state(max_same=2)
        s.pin("host", "node-1")
        s.record_attempt("host")
        s.record_attempt("host")
        assert s.should_fallback("host") is True

    def test_no_fallback_before_max_attempts(self):
        s = _make_state(max_same=3)
        s.pin("host", "node-1")
        s.record_attempt("host")
        assert s.should_fallback("host") is False

    def test_fallback_disabled(self):
        s = _make_state(max_same=1, fallback=False)
        s.record_attempt("host")
        assert s.should_fallback("host") is False

    def test_clear_resets_state(self):
        s = _make_state()
        s.pin("host", "node-1")
        s.record_attempt("host")
        s.clear("host")
        assert s.get_pinned_node("host") is None
        assert s.attempt_count("host") == 0


# ---------------------------------------------------------------------------
# Hook integration
# ---------------------------------------------------------------------------

class TestAttachStickyHooks:
    def setup_method(self):
        self.cfg = StickyConfig(key="host", max_same_node_attempts=2)
        self.state = StickyState(config=self.cfg)
        self.registry = HookRegistry()
        attach_sticky_hooks(self.registry, self.cfg, self.state)

    def test_on_retry_records_attempt(self):
        self.state.pin("host", "node-1")
        ctx = _FakeCtx()
        self.registry.fire_on_retry(_FakeResult(), ctx)
        assert self.state.attempt_count("host") == 1

    def test_on_retry_sets_sticky_node_in_metadata(self):
        self.state.pin("host", "node-7")
        ctx = _FakeCtx()
        self.registry.fire_on_retry(_FakeResult(), ctx)
        assert ctx.metadata.get("sticky_node") == "node-7"

    def test_on_retry_sets_fallback_flag_when_exhausted(self):
        self.state.pin("host", "node-1")
        ctx = _FakeCtx()
        self.registry.fire_on_retry(_FakeResult(), ctx)
        self.registry.fire_on_retry(_FakeResult(), ctx)
        assert ctx.metadata.get("sticky_fallback") is True

    def test_on_success_clears_state(self):
        self.state.pin("host", "node-1")
        self.state.record_attempt("host")
        ctx = _FakeCtx()
        self.registry.fire_on_success(_FakeResult(), ctx)
        assert self.state.get_pinned_node("host") is None

    def test_on_final_failure_clears_state(self):
        self.state.pin("host", "node-1")
        ctx = _FakeCtx()
        self.registry.fire_on_final_failure(_FakeResult(), ctx)
        assert self.state.get_pinned_node("host") is None
