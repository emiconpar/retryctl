"""Tests for CommandExecutor retry logic."""

import subprocess
from unittest.mock import MagicMock, call, patch

import pytest

from retryctl.backoff import BackoffConfig, BackoffStrategy
from retryctl.executor import CommandExecutor, ExecutionResult, RetryConfig


def _make_executor(max_attempts=3, retry_on_codes=None, stop_on_codes=None, strategy="fixed", base_delay=0.0):
    cfg = BackoffConfig(strategy=strategy, base_delay=base_delay, max_delay=10.0)
    backoff = BackoffStrategy(cfg)
    retry_cfg = RetryConfig(
        max_attempts=max_attempts,
        retry_on_codes=retry_on_codes or [],
        stop_on_codes=stop_on_codes or [],
    )
    return CommandExecutor(backoff=backoff, config=retry_cfg)


class TestSuccessOnFirstAttempt:
    def test_returns_succeeded_true(self):
        executor = _make_executor()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
            result = executor.run(["echo", "ok"])
        assert result.succeeded is True
        assert result.attempts == 1
        assert result.returncode == 0

    def test_stdout_captured(self):
        executor = _make_executor()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="")
            result = executor.run(["echo", "hello"])
        assert result.stdout == "hello"


class TestRetryOnFailure:
    def test_retries_up_to_max_attempts(self):
        executor = _make_executor(max_attempts=3)
        with patch("subprocess.run") as mock_run:
            with patch("time.sleep"):
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="err")
                result = executor.run(["false"])
        assert result.attempts == 3
        assert result.succeeded is False

    def test_succeeds_on_second_attempt(self):
        executor = _make_executor(max_attempts=3)
        side_effects = [
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="ok", stderr=""),
        ]
        with patch("subprocess.run", side_effect=side_effects):
            with patch("time.sleep"):
                result = executor.run(["cmd"])
        assert result.succeeded is True
        assert result.attempts == 2


class TestStopOnCodes:
    def test_stops_immediately_on_stop_code(self):
        executor = _make_executor(max_attempts=5, stop_on_codes=[2])
        with patch("subprocess.run") as mock_run:
            with patch("time.sleep") as mock_sleep:
                mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="")
                result = executor.run(["cmd"])
        assert result.attempts == 1
        mock_sleep.assert_not_called()


class TestRetryOnCodes:
    def test_does_not_retry_on_unlisted_code(self):
        executor = _make_executor(max_attempts=5, retry_on_codes=[1])
        with patch("subprocess.run") as mock_run:
            with patch("time.sleep") as mock_sleep:
                mock_run.return_value = MagicMock(returncode=2, stdout="", stderr="")
                result = executor.run(["cmd"])
        assert result.attempts == 1
        mock_sleep.assert_not_called()


class TestTimeout:
    def test_timeout_returns_failure(self):
        executor = _make_executor(max_attempts=1)
        executor.config.timeout = 0.001
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="cmd", timeout=0.001)):
            result = executor.run(["sleep", "10"])
        assert result.succeeded is False
        assert result.returncode == -1
