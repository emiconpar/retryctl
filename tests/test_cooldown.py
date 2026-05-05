"""Tests for retryctl.cooldown."""
from __future__ import annotations

import pytest

from retryctl.cooldown import (
    CooldownActive,
    CooldownConfig,
    CooldownEnforcer,
    CooldownState,
)


# ---------------------------------------------------------------------------
# CooldownConfig
# ---------------------------------------------------------------------------

class TestCooldownConfig:
    def test_valid_config_accepted(self):
        cfg = CooldownConfig(duration=30.0, key="cmd-foo")
        assert cfg.duration == 30.0
        assert cfg.key == "cmd-foo"

    def test_zero_duration_raises(self):
        with pytest.raises(ValueError, match="duration must be positive"):
            CooldownConfig(duration=0.0)

    def test_negative_duration_raises(self):
        with pytest.raises(ValueError, match="duration must be positive"):
            CooldownConfig(duration=-5.0)

    def test_empty_key_raises(self):
        with pytest.raises(ValueError, match="key must not be empty"):
            CooldownConfig(duration=10.0, key="")


# ---------------------------------------------------------------------------
# CooldownState
# ---------------------------------------------------------------------------

class TestCooldownState:
    def test_is_active_before_expiry(self):
        state = CooldownState(key="k", expires_at=100.0, duration=10.0)
        assert state.is_active(now=90.0) is True

    def test_is_not_active_after_expiry(self):
        state = CooldownState(key="k", expires_at=100.0, duration=10.0)
        assert state.is_active(now=100.0) is False
        assert state.is_active(now=101.0) is False

    def test_remaining_returns_correct_seconds(self):
        state = CooldownState(key="k", expires_at=100.0, duration=10.0)
        assert state.remaining(now=95.0) == pytest.approx(5.0)

    def test_remaining_never_negative(self):
        state = CooldownState(key="k", expires_at=100.0, duration=10.0)
        assert state.remaining(now=200.0) == 0.0


# ---------------------------------------------------------------------------
# CooldownEnforcer
# ---------------------------------------------------------------------------

class TestCooldownEnforcer:
    def _make_enforcer(self) -> CooldownEnforcer:
        return CooldownEnforcer()

    def test_no_cooldown_initially(self):
        enforcer = self._make_enforcer()
        enforcer.check("any-key", now=0.0)  # should not raise

    def test_cooldown_active_after_failure(self):
        enforcer = self._make_enforcer()
        cfg = CooldownConfig(duration=60.0, key="cmd")
        enforcer.record_failure(cfg, now=0.0)
        with pytest.raises(CooldownActive) as exc_info:
            enforcer.check("cmd", now=30.0)
        assert exc_info.value.remaining == pytest.approx(30.0)

    def test_cooldown_clears_after_expiry(self):
        enforcer = self._make_enforcer()
        cfg = CooldownConfig(duration=10.0, key="cmd")
        enforcer.record_failure(cfg, now=0.0)
        enforcer.check("cmd", now=10.0)  # exactly at expiry — should not raise

    def test_manual_clear_removes_cooldown(self):
        enforcer = self._make_enforcer()
        cfg = CooldownConfig(duration=60.0, key="cmd")
        enforcer.record_failure(cfg, now=0.0)
        enforcer.clear("cmd")
        enforcer.check("cmd", now=1.0)  # should not raise

    def test_state_for_returns_none_when_absent(self):
        enforcer = self._make_enforcer()
        assert enforcer.state_for("missing") is None

    def test_state_for_returns_state_after_failure(self):
        enforcer = self._make_enforcer()
        cfg = CooldownConfig(duration=20.0, key="cmd")
        enforcer.record_failure(cfg, now=0.0)
        state = enforcer.state_for("cmd")
        assert state is not None
        assert state.duration == 20.0

    def test_cooldown_active_exception_message(self):
        exc = CooldownActive(remaining=7.5)
        assert "7.50" in str(exc)
