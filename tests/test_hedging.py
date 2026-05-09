"""Tests for retryctl.hedging."""
from __future__ import annotations

import pytest

from retryctl.hedging import HedgeLog, HedgeRecord, HedgingConfig


# ---------------------------------------------------------------------------
# HedgingConfig
# ---------------------------------------------------------------------------

class TestHedgingConfig:
    def test_valid_config_accepted(self):
        cfg = HedgingConfig(delay=0.5, max_hedges=2)
        assert cfg.delay == 0.5
        assert cfg.max_hedges == 2

    def test_zero_delay_raises(self):
        with pytest.raises(ValueError, match="delay must be positive"):
            HedgingConfig(delay=0.0)

    def test_negative_delay_raises(self):
        with pytest.raises(ValueError, match="delay must be positive"):
            HedgingConfig(delay=-1.0)

    def test_zero_max_hedges_raises(self):
        with pytest.raises(ValueError, match="max_hedges must be at least 1"):
            HedgingConfig(delay=1.0, max_hedges=0)

    def test_defaults_are_sensible(self):
        cfg = HedgingConfig(delay=1.0)
        assert cfg.max_hedges == 1
        assert cfg.cancel_on_success is True


# ---------------------------------------------------------------------------
# HedgeRecord
# ---------------------------------------------------------------------------

def _make_record(**kwargs) -> HedgeRecord:
    defaults = dict(hedge_index=1, fired_at=1000.0, succeeded=False)
    defaults.update(kwargs)
    return HedgeRecord(**defaults)


class TestHedgeRecord:
    def test_to_dict_required_fields(self):
        r = _make_record()
        d = r.to_dict()
        assert d["hedge_index"] == 1
        assert d["fired_at"] == 1000.0
        assert d["succeeded"] is False

    def test_to_dict_excludes_none_exit_code(self):
        r = _make_record(exit_code=None)
        assert "exit_code" not in r.to_dict()

    def test_to_dict_includes_exit_code_when_set(self):
        r = _make_record(exit_code=1)
        assert r.to_dict()["exit_code"] == 1


# ---------------------------------------------------------------------------
# HedgeLog
# ---------------------------------------------------------------------------

class TestHedgeLog:
    def test_record_appends(self):
        log = HedgeLog()
        log.record(_make_record(hedge_index=1))
        log.record(_make_record(hedge_index=2))
        assert len(log.records) == 2

    def test_any_succeeded_false_when_empty(self):
        assert HedgeLog().any_succeeded() is False

    def test_any_succeeded_false_when_all_failed(self):
        log = HedgeLog()
        log.record(_make_record(succeeded=False))
        assert log.any_succeeded() is False

    def test_any_succeeded_true_when_one_succeeded(self):
        log = HedgeLog()
        log.record(_make_record(succeeded=False))
        log.record(_make_record(succeeded=True))
        assert log.any_succeeded() is True

    def test_to_dict_structure(self):
        log = HedgeLog()
        log.record(_make_record(hedge_index=1))
        d = log.to_dict()
        assert "hedges" in d
        assert len(d["hedges"]) == 1
