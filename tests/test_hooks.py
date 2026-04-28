"""Tests for retryctl.hooks."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from retryctl.executor import ExecutionResult
from retryctl.hooks import HookContext, HookRegistry, build_logging_hooks


def _make_result(exit_code: int = 0, succeeded: bool = True) -> ExecutionResult:
    return ExecutionResult(
        succeeded=succeeded,
        exit_code=exit_code,
        stdout="",
        stderr="",
        attempts=1,
        total_wait=0.0,
    )


def _make_ctx(
    attempt: int = 1,
    exit_code: int = 1,
    next_delay: float | None = 1.0,
) -> HookContext:
    return HookContext(
        attempt=attempt,
        result=_make_result(exit_code=exit_code, succeeded=(exit_code == 0)),
        next_delay=next_delay,
    )


class TestHookRegistry:
    def test_on_attempt_failure_called(self):
        registry = HookRegistry()
        spy = MagicMock()
        registry.register_on_attempt_failure(spy)
        ctx = _make_ctx()
        registry.fire_attempt_failure(ctx)
        spy.assert_called_once_with(ctx)

    def test_on_retry_called(self):
        registry = HookRegistry()
        spy = MagicMock()
        registry.register_on_retry(spy)
        ctx = _make_ctx()
        registry.fire_retry(ctx)
        spy.assert_called_once_with(ctx)

    def test_on_final_failure_called(self):
        registry = HookRegistry()
        spy = MagicMock()
        registry.register_on_final_failure(spy)
        ctx = _make_ctx(next_delay=None)
        registry.fire_final_failure(ctx)
        spy.assert_called_once_with(ctx)

    def test_on_success_called(self):
        registry = HookRegistry()
        spy = MagicMock()
        registry.register_on_success(spy)
        ctx = _make_ctx(exit_code=0)
        registry.fire_success(ctx)
        spy.assert_called_once_with(ctx)

    def test_multiple_hooks_all_called(self):
        registry = HookRegistry()
        spy1, spy2 = MagicMock(), MagicMock()
        registry.register_on_attempt_failure(spy1)
        registry.register_on_attempt_failure(spy2)
        ctx = _make_ctx()
        registry.fire_attempt_failure(ctx)
        spy1.assert_called_once()
        spy2.assert_called_once()

    def test_no_hooks_does_not_raise(self):
        registry = HookRegistry()
        ctx = _make_ctx()
        registry.fire_attempt_failure(ctx)  # should not raise


class TestBuildLoggingHooks:
    def test_returns_hook_registry(self):
        registry = build_logging_hooks()
        assert isinstance(registry, HookRegistry)

    def test_failure_hook_writes_to_stderr(self, capsys):
        registry = build_logging_hooks()
        ctx = _make_ctx(attempt=2, exit_code=1)
        registry.fire_attempt_failure(ctx)
        captured = capsys.readouterr()
        assert "attempt 2" in captured.err
        assert "exit code 1" in captured.err

    def test_retry_hook_writes_delay_to_stderr(self, capsys):
        registry = build_logging_hooks()
        ctx = _make_ctx(attempt=1, next_delay=2.5)
        registry.fire_retry(ctx)
        captured = capsys.readouterr()
        assert "2.50" in captured.err

    def test_success_hook_silent_by_default(self, capsys):
        registry = build_logging_hooks(verbose=False)
        ctx = _make_ctx(exit_code=0)
        registry.fire_success(ctx)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_success_hook_verbose_writes_to_stderr(self, capsys):
        registry = build_logging_hooks(verbose=True)
        ctx = _make_ctx(exit_code=0)
        registry.fire_success(ctx)
        captured = capsys.readouterr()
        assert "succeeded" in captured.err
