"""Tests for retryctl.fallback and retryctl.fallback_hook."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from retryctl.executor import ExecutionResult
from retryctl.fallback import FallbackConfig, FallbackResult, run_fallback
from retryctl.fallback_hook import attach_fallback_hooks
from retryctl.hooks import HookContext, HookRegistry


# ---------------------------------------------------------------------------
# FallbackConfig validation
# ---------------------------------------------------------------------------

class TestFallbackConfig:
    def test_valid_config_accepted(self):
        cfg = FallbackConfig(command=["echo", "hi"])
        assert cfg.command == ["echo", "hi"]

    def test_empty_command_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            FallbackConfig(command=[])

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout must be positive"):
            FallbackConfig(command=["echo"], timeout=0.0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout must be positive"):
            FallbackConfig(command=["echo"], timeout=-1.0)

    def test_positive_timeout_accepted(self):
        cfg = FallbackConfig(command=["echo"], timeout=5.0)
        assert cfg.timeout == 5.0


# ---------------------------------------------------------------------------
# run_fallback
# ---------------------------------------------------------------------------

class TestRunFallback:
    def test_successful_command_returns_exit_code(self):
        cfg = FallbackConfig(command=[sys.executable, "-c", "raise SystemExit(0)"])
        result = run_fallback(cfg)
        assert result.exit_code == 0
        assert result.ran is True

    def test_failing_command_returns_nonzero(self):
        cfg = FallbackConfig(command=[sys.executable, "-c", "raise SystemExit(3)"])
        result = run_fallback(cfg)
        assert result.exit_code == 3

    def test_missing_command_returns_127(self):
        cfg = FallbackConfig(command=["/no/such/binary"])
        result = run_fallback(cfg)
        assert result.exit_code == 127
        assert result.ran is False

    def test_timeout_returns_124(self):
        cfg = FallbackConfig(
            command=[sys.executable, "-c", "import time; time.sleep(10)"],
            timeout=0.05,
        )
        result = run_fallback(cfg)
        assert result.exit_code == 124
        assert "timed out" in result.stderr


# ---------------------------------------------------------------------------
# attach_fallback_hooks
# ---------------------------------------------------------------------------

def _make_result() -> ExecutionResult:
    return ExecutionResult(
        command=["false"],
        succeeded=False,
        exit_code=1,
        stdout="",
        stderr="",
        attempts=3,
    )


def _make_ctx() -> HookContext:
    return HookContext(attempt=3, result=_make_result(), delay=0.0)


class TestAttachFallbackHooks:
    def setup_method(self):
        self.registry = HookRegistry()

    def test_fallback_runs_on_final_failure(self):
        cfg = FallbackConfig(command=[sys.executable, "-c", "raise SystemExit(0)"])
        received: list[FallbackResult] = []
        attach_fallback_hooks(self.registry, cfg, on_fallback=received.append)
        self.registry.fire_final_failure(_make_ctx())
        assert len(received) == 1
        assert received[0].exit_code == 0

    def test_on_fallback_callback_optional(self):
        cfg = FallbackConfig(command=[sys.executable, "-c", "raise SystemExit(0)"])
        attach_fallback_hooks(self.registry, cfg)
        # Should not raise even without a callback
        self.registry.fire_final_failure(_make_ctx())

    def test_fallback_not_triggered_before_final_failure(self):
        cfg = FallbackConfig(command=[sys.executable, "-c", "raise SystemExit(0)"])
        received: list[FallbackResult] = []
        attach_fallback_hooks(self.registry, cfg, on_fallback=received.append)
        # Firing attempt_failure and retry should NOT trigger fallback
        self.registry.fire_attempt_failure(_make_ctx())
        self.registry.fire_retry(_make_ctx())
        assert len(received) == 0
