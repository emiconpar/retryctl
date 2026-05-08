"""Tests for retryctl.costguard and retryctl.costguard_hook."""
from __future__ import annotations

import pytest

from retryctl.costguard import (
    CostGuardConfig,
    CostGuardExceeded,
    CostGuardState,
    check_cost,
)
from retryctl.costguard_hook import attach_costguard_hooks
from retryctl.hooks import HookContext, HookRegistry
from retryctl.executor import ExecutionResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_result(exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        succeeded=False,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
    )


def _make_ctx(attempt: int = 1, delay: float = 1.0) -> HookContext:
    return HookContext(attempt=attempt, delay=delay)


# ---------------------------------------------------------------------------
# CostGuardConfig
# ---------------------------------------------------------------------------

class TestCostGuardConfig:
    def test_valid_config_accepted(self):
        cfg = CostGuardConfig(max_cost=10.0)
        assert cfg.max_cost == 10.0

    def test_zero_max_cost_raises(self):
        with pytest.raises(ValueError, match="max_cost must be positive"):
            CostGuardConfig(max_cost=0.0)

    def test_negative_max_cost_raises(self):
        with pytest.raises(ValueError, match="max_cost must be positive"):
            CostGuardConfig(max_cost=-5.0)

    def test_custom_cost_fn_accepted(self):
        cfg = CostGuardConfig(max_cost=100.0, cost_fn=lambda a, d: a * 2.0)
        assert cfg.cost_fn(3, 0.0) == 6.0


# ---------------------------------------------------------------------------
# CostGuardState
# ---------------------------------------------------------------------------

class TestCostGuardState:
    def test_initial_total_is_zero(self):
        assert CostGuardState().total == 0.0

    def test_add_accumulates(self):
        s = CostGuardState()
        s.add(1.5)
        s.add(2.5)
        assert s.total == pytest.approx(4.0)

    def test_negative_amount_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            CostGuardState().add(-0.1)

    def test_reset_clears_total(self):
        s = CostGuardState()
        s.add(9.9)
        s.reset()
        assert s.total == 0.0


# ---------------------------------------------------------------------------
# check_cost
# ---------------------------------------------------------------------------

class TestCheckCost:
    def test_under_budget_does_not_raise(self):
        cfg = CostGuardConfig(max_cost=10.0)
        state = CostGuardState()
        check_cost(state, cfg, attempt=1, delay=3.0)  # cost == 3.0

    def test_exactly_at_budget_does_not_raise(self):
        cfg = CostGuardConfig(max_cost=5.0)
        state = CostGuardState()
        check_cost(state, cfg, attempt=1, delay=5.0)

    def test_over_budget_raises(self):
        cfg = CostGuardConfig(max_cost=4.0)
        state = CostGuardState()
        with pytest.raises(CostGuardExceeded) as exc_info:
            check_cost(state, cfg, attempt=1, delay=5.0)
        assert exc_info.value.total > exc_info.value.limit

    def test_cumulative_tracking(self):
        cfg = CostGuardConfig(max_cost=5.0)
        state = CostGuardState()
        check_cost(state, cfg, attempt=1, delay=2.0)
        check_cost(state, cfg, attempt=2, delay=2.0)
        with pytest.raises(CostGuardExceeded):
            check_cost(state, cfg, attempt=3, delay=2.0)


# ---------------------------------------------------------------------------
# attach_costguard_hooks
# ---------------------------------------------------------------------------

class TestAttachCostguardHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.config = CostGuardConfig(max_cost=5.0)

    def test_returns_state(self):
        state = attach_costguard_hooks(self.registry, self.config)
        assert isinstance(state, CostGuardState)

    def test_accepts_external_state(self):
        external = CostGuardState()
        returned = attach_costguard_hooks(self.registry, self.config, state=external)
        assert returned is external

    def test_on_retry_accumulates_cost(self):
        state = attach_costguard_hooks(self.registry, self.config)
        self.registry.fire_on_retry(_make_result(), _make_ctx(attempt=1, delay=2.0))
        assert state.total == pytest.approx(2.0)

    def test_on_retry_raises_when_over_budget(self):
        state = attach_costguard_hooks(self.registry, self.config)
        with pytest.raises(CostGuardExceeded):
            self.registry.fire_on_retry(_make_result(), _make_ctx(attempt=1, delay=6.0))
