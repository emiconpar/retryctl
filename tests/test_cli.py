"""Tests for the CLI entry point (retryctl/cli.py)."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from retryctl.cli import main
from retryctl.executor import ExecutionResult


def _make_result(
    succeeded=True,
    exit_code=0,
    attempts=1,
    stdout="",
    stderr="",
    total_duration=0.1,
):
    """Helper to build a minimal ExecutionResult for testing."""
    return ExecutionResult(
        succeeded=succeeded,
        exit_code=exit_code,
        attempts=attempts,
        stdout=stdout,
        stderr=stderr,
        total_duration=total_duration,
    )


class TestCLIArgumentParsing:
    """Verify that the CLI correctly parses arguments and delegates to runner."""

    def test_exits_zero_on_success(self):
        result = _make_result(succeeded=True, exit_code=0)
        with patch("retryctl.cli.run_command", return_value=result):
            with pytest.raises(SystemExit) as exc_info:
                main(["echo", "hello"])
        assert exc_info.value.code == 0

    def test_exits_with_command_exit_code_on_failure(self):
        result = _make_result(succeeded=False, exit_code=2)
        with patch("retryctl.cli.run_command", return_value=result):
            with pytest.raises(SystemExit) as exc_info:
                main(["false"])
        assert exc_info.value.code == 2

    def test_passes_max_attempts_to_runner(self):
        result = _make_result()
        with patch("retryctl.cli.run_command", return_value=result) as mock_run:
            with pytest.raises(SystemExit):
                main(["--max-attempts", "5", "echo"])
        _, kwargs = mock_run.call_args
        assert kwargs.get("max_attempts") == 5 or mock_run.call_args[0][1] == 5

    def test_passes_strategy_to_runner(self):
        result = _make_result()
        with patch("retryctl.cli.run_command", return_value=result) as mock_run:
            with pytest.raises(SystemExit):
                main(["--strategy", "exponential", "echo"])
        args, kwargs = mock_run.call_args
        strategy_val = kwargs.get("strategy") or (args[2] if len(args) > 2 else None)
        assert strategy_val == "exponential"

    def test_default_max_attempts_is_three(self):
        result = _make_result()
        with patch("retryctl.cli.run_command", return_value=result) as mock_run:
            with pytest.raises(SystemExit):
                main(["echo", "hi"])
        args, kwargs = mock_run.call_args
        attempts_val = kwargs.get("max_attempts") or (args[1] if len(args) > 1 else None)
        assert attempts_val == 3

    def test_default_strategy_is_fixed(self):
        result = _make_result()
        with patch("retryctl.cli.run_command", return_value=result) as mock_run:
            with pytest.raises(SystemExit):
                main(["echo"])
        args, kwargs = mock_run.call_args
        strategy_val = kwargs.get("strategy") or (args[2] if len(args) > 2 else None)
        assert strategy_val == "fixed"


class TestCLIOutputFormat:
    """Verify that output format flags are respected."""

    def test_json_flag_accepted(self):
        result = _make_result()
        with patch("retryctl.cli.run_command", return_value=result):
            with patch("retryctl.cli.format_result", return_value="{}") as mock_fmt:
                with patch("builtins.print"):
                    with pytest.raises(SystemExit):
                        main(["--format", "json", "echo"])
        mock_fmt.assert_called_once()
        fmt_arg = mock_fmt.call_args[0][1] if mock_fmt.call_args[0] else mock_fmt.call_args[1].get("fmt")
        assert str(fmt_arg).lower() in ("json", "outputformat.json")

    def test_text_format_is_default(self):
        result = _make_result()
        with patch("retryctl.cli.run_command", return_value=result):
            with patch("retryctl.cli.format_result", return_value="ok") as mock_fmt:
                with patch("builtins.print"):
                    with pytest.raises(SystemExit):
                        main(["echo"])
        mock_fmt.assert_called_once()
        fmt_arg = mock_fmt.call_args[0][1] if mock_fmt.call_args[0] else mock_fmt.call_args[1].get("fmt")
        assert str(fmt_arg).lower() in ("text", "outputformat.text")
