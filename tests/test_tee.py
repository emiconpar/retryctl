"""Tests for retryctl.tee."""
from __future__ import annotations

import pytest

from retryctl.tee import TeeConfig, TeeRecord, apply_tee


# ---------------------------------------------------------------------------
# TeeConfig validation
# ---------------------------------------------------------------------------

class TestTeeConfig:
    def test_valid_config_accepted(self):
        cfg = TeeConfig(enabled=True, stream="both")
        assert cfg.enabled is True
        assert cfg.stream == "both"

    def test_stdout_stream_accepted(self):
        cfg = TeeConfig(stream="stdout")
        assert cfg.stream == "stdout"

    def test_stderr_stream_accepted(self):
        cfg = TeeConfig(stream="stderr")
        assert cfg.stream == "stderr"

    def test_invalid_stream_raises(self):
        with pytest.raises(ValueError, match="stream must be one of"):
            TeeConfig(stream="all")

    def test_non_bool_enabled_raises(self):
        with pytest.raises(TypeError, match="enabled must be a bool"):
            TeeConfig(enabled=1)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TeeRecord
# ---------------------------------------------------------------------------

class TestTeeRecord:
    def test_to_dict_includes_all_fields(self):
        rec = TeeRecord(attempt=2, stdout_bytes=100, stderr_bytes=50)
        d = rec.to_dict()
        assert d["attempt"] == 2
        assert d["stdout_bytes"] == 100
        assert d["stderr_bytes"] == 50

    def test_defaults_are_zero(self):
        rec = TeeRecord(attempt=1)
        assert rec.stdout_bytes == 0
        assert rec.stderr_bytes == 0


# ---------------------------------------------------------------------------
# apply_tee
# ---------------------------------------------------------------------------

def _collect_sink():
    calls: list[tuple[str, str]] = []

    def sink(stream: str, text: str) -> None:
        calls.append((stream, text))

    return sink, calls


class TestApplyTee:
    def test_disabled_config_returns_empty_record(self):
        cfg = TeeConfig(enabled=False)
        rec = apply_tee(cfg, attempt=1, stdout="hello", stderr="err", sink=lambda s, t: None)
        assert rec.stdout_bytes == 0
        assert rec.stderr_bytes == 0

    def test_both_streams_written(self):
        cfg = TeeConfig(stream="both")
        sink, calls = _collect_sink()
        rec = apply_tee(cfg, attempt=1, stdout="out", stderr="err", sink=sink)
        streams = [c[0] for c in calls]
        assert "stdout" in streams
        assert "stderr" in streams
        assert rec.stdout_bytes > 0
        assert rec.stderr_bytes > 0

    def test_stdout_only_stream(self):
        cfg = TeeConfig(stream="stdout")
        sink, calls = _collect_sink()
        apply_tee(cfg, attempt=1, stdout="out", stderr="err", sink=sink)
        assert all(c[0] == "stdout" for c in calls)

    def test_stderr_only_stream(self):
        cfg = TeeConfig(stream="stderr")
        sink, calls = _collect_sink()
        apply_tee(cfg, attempt=1, stdout="out", stderr="err", sink=sink)
        assert all(c[0] == "stderr" for c in calls)

    def test_empty_stdout_not_written(self):
        cfg = TeeConfig(stream="both")
        sink, calls = _collect_sink()
        apply_tee(cfg, attempt=1, stdout="", stderr="err", sink=sink)
        assert not any(c[0] == "stdout" for c in calls)

    def test_byte_count_matches_utf8_length(self):
        cfg = TeeConfig(stream="stdout")
        sink, _ = _collect_sink()
        text = "héllo"
        rec = apply_tee(cfg, attempt=1, stdout=text, stderr="", sink=sink)
        assert rec.stdout_bytes == len(text.encode())

    def test_attempt_number_stored(self):
        cfg = TeeConfig(stream="both")
        sink, _ = _collect_sink()
        rec = apply_tee(cfg, attempt=3, stdout="x", stderr="y", sink=sink)
        assert rec.attempt == 3
