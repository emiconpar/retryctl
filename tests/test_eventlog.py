"""Tests for EventLog and attach_eventlog_hooks."""
from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from retryctl.eventlog import EventLog, EventLogEntry
from retryctl.eventlog_hook import attach_eventlog_hooks
from retryctl.hooks import HookRegistry


def _make_result(exit_code: int = 1):
    r = MagicMock()
    r.exit_code = exit_code
    return r


def _make_ctx(attempt: int = 1, last_delay: float = 0.5):
    ctx = MagicMock()
    ctx.attempt = attempt
    ctx.last_delay = last_delay
    return ctx


class TestEventLogEntry:
    def test_to_dict_includes_required_fields(self):
        entry = EventLogEntry(event_type="retry", attempt=2)
        d = entry.to_dict()
        assert d["event_type"] == "retry"
        assert d["attempt"] == 2
        assert "timestamp" in d

    def test_to_dict_excludes_none_optional_fields(self):
        entry = EventLogEntry(event_type="success", attempt=1)
        d = entry.to_dict()
        assert "exit_code" not in d
        assert "delay" not in d
        assert "message" not in d
        assert "extra" not in d

    def test_to_dict_includes_present_optional_fields(self):
        entry = EventLogEntry(event_type="failure", attempt=3, exit_code=2, delay=1.5)
        d = entry.to_dict()
        assert d["exit_code"] == 2
        assert d["delay"] == 1.5

    def test_from_dict_round_trips(self):
        entry = EventLogEntry(
            event_type="retry", attempt=2, exit_code=1, delay=0.5, message="hi"
        )
        restored = EventLogEntry.from_dict(entry.to_dict())
        assert restored.event_type == entry.event_type
        assert restored.attempt == entry.attempt
        assert restored.exit_code == entry.exit_code
        assert restored.delay == entry.delay

    def test_timestamp_is_recent(self):
        before = time.time()
        entry = EventLogEntry(event_type="x", attempt=1)
        after = time.time()
        assert before <= entry.timestamp <= after


class TestEventLog:
    def test_record_and_entries(self):
        log = EventLog()
        entry = EventLogEntry(event_type="success", attempt=1)
        log.record(entry)
        assert len(log) == 1
        assert log.entries()[0] is entry

    def test_entries_by_type(self):
        log = EventLog()
        log.record(EventLogEntry(event_type="retry", attempt=1))
        log.record(EventLogEntry(event_type="success", attempt=2))
        retries = log.entries_by_type("retry")
        assert len(retries) == 1
        assert retries[0].event_type == "retry"

    def test_clear_removes_all(self):
        log = EventLog()
        log.record(EventLogEntry(event_type="retry", attempt=1))
        log.clear()
        assert len(log) == 0


class TestAttachEventlogHooks:
    def setup_method(self):
        self.log = EventLog()
        self.registry = HookRegistry()
        attach_eventlog_hooks(self.registry, self.log)

    def test_attempt_failure_records_entry(self):
        self.registry.fire_on_attempt_failure(_make_result(1), _make_ctx(1))
        assert len(self.log.entries_by_type("attempt_failure")) == 1

    def test_retry_records_entry_with_delay(self):
        self.registry.fire_on_retry(_make_result(1), _make_ctx(2, last_delay=1.0))
        entries = self.log.entries_by_type("retry")
        assert len(entries) == 1
        assert entries[0].delay == 1.0

    def test_final_failure_records_entry(self):
        self.registry.fire_on_final_failure(_make_result(1), _make_ctx(3))
        assert len(self.log.entries_by_type("final_failure")) == 1

    def test_success_records_entry(self):
        self.registry.fire_on_success(_make_result(0), _make_ctx(1))
        entries = self.log.entries_by_type("success")
        assert len(entries) == 1
        assert entries[0].exit_code == 0
