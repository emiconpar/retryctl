"""Tests for retryctl.formatter."""

from __future__ import annotations

import json

import pytest

from retryctl.executor import ExecutionResult
from retryctl.formatter import OutputFormat, format_result


def _make_result(**kwargs) -> ExecutionResult:
    defaults = dict(
        succeeded=True,
        exit_code=0,
        attempts=1,
        stdout="hello\n",
        stderr="",
        elapsed=0.123,
    )
    defaults.update(kwargs)
    return ExecutionResult(**defaults)


class TestTextFormat:
    def test_contains_status_succeeded(self):
        out = format_result(_make_result(), OutputFormat.TEXT)
        assert "succeeded" in out

    def test_contains_exit_code(self):
        out = format_result(_make_result(exit_code=0), OutputFormat.TEXT)
        assert "Exit code: 0" in out

    def test_contains_attempts(self):
        out = format_result(_make_result(attempts=3), OutputFormat.TEXT)
        assert "Attempts : 3" in out

    def test_shows_failed_status(self):
        out = format_result(_make_result(succeeded=False, exit_code=1), OutputFormat.TEXT)
        assert "failed" in out

    def test_stdout_included_when_present(self):
        out = format_result(_make_result(stdout="output line"), OutputFormat.TEXT)
        assert "output line" in out

    def test_stderr_omitted_when_empty(self):
        out = format_result(_make_result(stderr=""), OutputFormat.TEXT)
        assert "Stderr" not in out


class TestJsonFormat:
    def test_valid_json(self):
        out = format_result(_make_result(), OutputFormat.JSON)
        data = json.loads(out)  # must not raise
        assert isinstance(data, dict)

    def test_json_has_required_keys(self):
        out = format_result(_make_result(), OutputFormat.JSON)
        data = json.loads(out)
        for key in ("succeeded", "exit_code", "attempts", "stdout", "stderr", "elapsed"):
            assert key in data

    def test_json_elapsed_rounded(self):
        out = format_result(_make_result(elapsed=1.23456789), OutputFormat.JSON)
        data = json.loads(out)
        assert data["elapsed"] == 1.2346


class TestQuietFormat:
    def test_quiet_returns_empty_string(self):
        out = format_result(_make_result(), OutputFormat.QUIET)
        assert out == ""
