"""Tests for retryctl.metrics_reporter."""
from __future__ import annotations

import io
import json

import pytest

from retryctl.metrics import RunMetrics
from retryctl.metrics_reporter import (
    JsonReporter,
    NullReporter,
    TextReporter,
    build_reporter,
)


def _make_metrics() -> RunMetrics:
    m = RunMetrics(command=["curl", "http://example.com"])
    m.record_attempt(1, exit_code=1, duration=0.1, delay_before_next=2.0)
    m.record_attempt(2, exit_code=0, duration=0.05)
    m.finish(succeeded=True, final_exit_code=0)
    return m


class TestNullReporter:
    def test_report_does_not_raise(self):
        NullReporter().report(_make_metrics())  # should not raise


class TestJsonReporter:
    def test_output_is_valid_json(self):
        buf = io.StringIO()
        JsonReporter(buf).report(_make_metrics())
        data = json.loads(buf.getvalue())
        assert data["succeeded"] is True

    def test_contains_attempts_array(self):
        buf = io.StringIO()
        JsonReporter(buf).report(_make_metrics())
        data = json.loads(buf.getvalue())
        assert len(data["attempts"]) == 2

    def test_ends_with_newline(self):
        buf = io.StringIO()
        JsonReporter(buf).report(_make_metrics())
        assert buf.getvalue().endswith("\n")


class TestTextReporter:
    def test_contains_status(self):
        buf = io.StringIO()
        TextReporter(buf).report(_make_metrics())
        assert "succeeded" in buf.getvalue()

    def test_contains_command(self):
        buf = io.StringIO()
        TextReporter(buf).report(_make_metrics())
        assert "curl" in buf.getvalue()

    def test_contains_attempt_lines(self):
        buf = io.StringIO()
        TextReporter(buf).report(_make_metrics())
        output = buf.getvalue()
        assert "attempt #1" in output
        assert "attempt #2" in output


class TestBuildReporter:
    def test_json_format(self):
        assert isinstance(build_reporter("json"), JsonReporter)

    def test_text_format(self):
        assert isinstance(build_reporter("text"), TextReporter)

    def test_none_format(self):
        assert isinstance(build_reporter("none"), NullReporter)

    def test_empty_string_format(self):
        assert isinstance(build_reporter(""), NullReporter)

    def test_unknown_format_raises(self):
        with pytest.raises(ValueError, match="Unknown metrics format"):
            build_reporter("prometheus")
