"""Tests for retryctl.spillover."""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from retryctl.spillover import (
    SpilloverConfig,
    SpilloverResult,
    run_spillover,
)


# ---------------------------------------------------------------------------
# SpilloverConfig validation
# ---------------------------------------------------------------------------

class TestSpilloverConfig:
    def test_valid_config_accepted(self):
        cfg = SpilloverConfig(command=["echo", "hi"])
        assert cfg.command == ["echo", "hi"]

    def test_empty_command_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            SpilloverConfig(command=[])

    def test_zero_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            SpilloverConfig(command=["echo"], max_attempts=0)

    def test_negative_max_attempts_raises(self):
        with pytest.raises(ValueError, match="max_attempts"):
            SpilloverConfig(command=["echo"], max_attempts=-1)

    def test_zero_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout"):
            SpilloverConfig(command=["echo"], timeout=0.0)

    def test_negative_timeout_raises(self):
        with pytest.raises(ValueError, match="timeout"):
            SpilloverConfig(command=["echo"], timeout=-5.0)

    def test_non_bool_enabled_raises(self):
        with pytest.raises(TypeError, match="enabled"):
            SpilloverConfig(command=["echo"], enabled="yes")  # type: ignore

    def test_none_timeout_allowed(self):
        cfg = SpilloverConfig(command=["echo"], timeout=None)
        assert cfg.timeout is None


# ---------------------------------------------------------------------------
# SpilloverResult
# ---------------------------------------------------------------------------

class TestSpilloverResult:
    def _make(self, exit_code=0):
        return SpilloverResult(
            command=["echo", "hi"],
            exit_code=exit_code,
            stdout="hi\n",
            stderr="",
            attempt=1,
        )

    def test_to_dict_contains_fields(self):
        r = self._make()
        d = r.to_dict()
        assert d["exit_code"] == 0
        assert d["triggered"] is True
        assert d["attempt"] == 1


# ---------------------------------------------------------------------------
# run_spillover
# ---------------------------------------------------------------------------

class TestRunSpillover:
    def _proc(self, returncode=0, stdout="ok", stderr=""):
        m = MagicMock()
        m.returncode = returncode
        m.stdout = stdout
        m.stderr = stderr
        return m

    def test_succeeds_on_first_attempt(self):
        cfg = SpilloverConfig(command=["echo", "ok"])
        with patch("retryctl.spillover.subprocess.run", return_value=self._proc()) as mock_run:
            result = run_spillover(cfg)
        assert result.exit_code == 0
        assert result.attempt == 1
        mock_run.assert_called_once()

    def test_retries_on_failure(self):
        cfg = SpilloverConfig(command=["false"], max_attempts=3)
        with patch("retryctl.spillover.subprocess.run", return_value=self._proc(returncode=1)) as mock_run:
            result = run_spillover(cfg)
        assert mock_run.call_count == 3
        assert result.attempt == 3

    def test_stops_early_on_success(self):
        cfg = SpilloverConfig(command=["cmd"], max_attempts=5)
        side_effects = [
            self._proc(returncode=1),
            self._proc(returncode=0),
        ]
        with patch("retryctl.spillover.subprocess.run", side_effect=side_effects) as mock_run:
            result = run_spillover(cfg)
        assert mock_run.call_count == 2
        assert result.exit_code == 0

    def test_timeout_returns_exit_code_124(self):
        import subprocess as sp
        cfg = SpilloverConfig(command=["sleep", "99"], timeout=0.001)
        with patch("retryctl.spillover.subprocess.run", side_effect=sp.TimeoutExpired(cmd="sleep", timeout=0.001)):
            result = run_spillover(cfg)
        assert result.exit_code == 124
        assert "timed out" in result.stderr
