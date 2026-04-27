"""Tests for the high-level runner module."""

from unittest.mock import MagicMock, patch

import pytest

from retryctl.executor import ExecutionResult
from retryctl.runner import build_executor, run_command


class TestBuildExecutor:
    def test_returns_command_executor(self):
        from retryctl.executor import CommandExecutor
        executor = build_executor()
        assert isinstance(executor, CommandExecutor)

    def test_respects_max_attempts(self):
        executor = build_executor(max_attempts=7)
        assert executor.config.max_attempts == 7

    def test_respects_strategy(self):
        executor = build_executor(strategy="fixed", base_delay=5.0)
        assert executor.backoff.config.strategy == "fixed"
        assert executor.backoff.config.base_delay == 5.0

    def test_retry_on_codes_passed_through(self):
        executor = build_executor(retry_on_codes=[1, 2, 3])
        assert executor.config.retry_on_codes == [1, 2, 3]

    def test_stop_on_codes_passed_through(self):
        executor = build_executor(stop_on_codes=[42])
        assert executor.config.stop_on_codes == [42]

    def test_jitter_flag(self):
        executor = build_executor(jitter=True)
        assert executor.backoff.config.jitter is True


class TestRunCommand:
    def test_delegates_to_executor(self):
        fake_result = ExecutionResult(
            command=["echo", "hi"],
            returncode=0,
            attempts=1,
            succeeded=True,
        )
        with patch("retryctl.runner.CommandExecutor.run", return_value=fake_result) as mock_run:
            result = run_command(["echo", "hi"], max_attempts=1, base_delay=0.0)
        mock_run.assert_called_once_with(["echo", "hi"])
        assert result.succeeded is True

    def test_failure_propagated(self):
        fake_result = ExecutionResult(
            command=["false"],
            returncode=1,
            attempts=3,
            succeeded=False,
        )
        with patch("retryctl.runner.CommandExecutor.run", return_value=fake_result):
            result = run_command(["false"], max_attempts=3, base_delay=0.0)
        assert result.succeeded is False
        assert result.attempts == 3
