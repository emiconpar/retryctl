"""Tests for retryctl.spillover_hook."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from retryctl.hooks import HookRegistry, HookContext
from retryctl.executor import ExecutionResult
from retryctl.spillover import SpilloverConfig, SpilloverResult
from retryctl.spillover_hook import attach_spillover_hooks


def _make_result(exit_code: int = 1) -> ExecutionResult:
    return ExecutionResult(
        succeeded=exit_code == 0,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=3,
        total_delay=1.0,
    )


def _make_ctx() -> HookContext:
    ctx = MagicMock(spec=HookContext)
    ctx.attempt = 3
    return ctx


def _make_spillover_result(exit_code: int = 0) -> SpilloverResult:
    return SpilloverResult(
        command=["fallback"],
        exit_code=exit_code,
        stdout="ok",
        stderr="",
        attempt=1,
    )


class TestAttachSpilloverHooks:
    def setup_method(self):
        self.registry = HookRegistry()
        self.config = SpilloverConfig(command=["fallback-cmd"])

    def test_final_failure_triggers_spillover(self):
        captured = []
        spill_result = _make_spillover_result()

        with patch("retryctl.spillover_hook.run_spillover", return_value=spill_result):
            attach_spillover_hooks(self.registry, self.config, on_spillover=captured.append)
            self.registry.fire_on_final_failure(_make_result(), _make_ctx())

        assert len(captured) == 1
        assert captured[0].exit_code == 0

    def test_on_spillover_callback_optional(self):
        spill_result = _make_spillover_result()
        with patch("retryctl.spillover_hook.run_spillover", return_value=spill_result):
            attach_spillover_hooks(self.registry, self.config)
            # Should not raise even without callback
            self.registry.fire_on_final_failure(_make_result(), _make_ctx())

    def test_disabled_config_skips_registration(self):
        cfg = SpilloverConfig(command=["fallback-cmd"], enabled=False)
        with patch("retryctl.spillover_hook.run_spillover") as mock_run:
            attach_spillover_hooks(self.registry, cfg)
            self.registry.fire_on_final_failure(_make_result(), _make_ctx())
        mock_run.assert_not_called()

    def test_retry_hook_not_registered(self):
        """Spillover only fires on final failure, not on each retry."""
        with patch("retryctl.spillover_hook.run_spillover") as mock_run:
            attach_spillover_hooks(self.registry, self.config)
            self.registry.fire_on_retry(_make_result(), _make_ctx())
        mock_run.assert_not_called()
