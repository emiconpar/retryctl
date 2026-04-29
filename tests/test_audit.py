"""Tests for retryctl.audit — AuditEvent / AuditLog."""
from __future__ import annotations

import io
import json
import time

import pytest

from retryctl.audit import AuditEvent, AuditLog, make_audit_event


def _make_event(**kwargs) -> AuditEvent:
    defaults = dict(attempt=1, exit_code=1, succeeded=False)
    defaults.update(kwargs)
    return make_audit_event(**defaults)


class TestAuditEvent:
    def test_timestamp_is_recent(self):
        before = time.time()
        ev = _make_event()
        assert ev.timestamp >= before

    def test_to_dict_excludes_none_fields(self):
        ev = _make_event(delay_before_next=None, signal=None, note=None)
        d = ev.to_dict()
        assert "delay_before_next" not in d
        assert "signal" not in d
        assert "note" not in d

    def test_to_dict_includes_present_fields(self):
        ev = _make_event(delay_before_next=2.5, note="retry_scheduled")
        d = ev.to_dict()
        assert d["delay_before_next"] == 2.5
        assert d["note"] == "retry_scheduled"

    def test_succeeded_stored(self):
        ev = _make_event(succeeded=True, exit_code=0)
        assert ev.succeeded is True
        assert ev.exit_code == 0


class TestAuditLog:
    def test_record_appends_event(self):
        log = AuditLog(command=["echo", "hi"])
        ev = _make_event()
        log.record(ev)
        assert len(log.events) == 1
        assert log.events[0] is ev

    def test_write_produces_valid_json(self):
        log = AuditLog(command=["ls"])
        log.record(_make_event(attempt=1, exit_code=2, succeeded=False, note="fail"))
        buf = io.StringIO()
        log.write(stream=buf)
        data = json.loads(buf.getvalue())
        assert data["command"] == ["ls"]
        assert len(data["events"]) == 1

    def test_write_includes_command(self):
        log = AuditLog(command=["curl", "http://example.com"])
        buf = io.StringIO()
        log.write(stream=buf)
        data = json.loads(buf.getvalue())
        assert data["command"] == ["curl", "http://example.com"]

    def test_multiple_events_preserved_in_order(self):
        log = AuditLog(command=["false"])
        for i in range(3):
            log.record(_make_event(attempt=i + 1))
        assert [e.attempt for e in log.events] == [1, 2, 3]
