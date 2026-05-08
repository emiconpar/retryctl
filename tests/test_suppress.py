"""Tests for retryctl.suppress."""
from __future__ import annotations

import pytest

from retryctl.suppress import (
    SuppressConfig,
    SuppressedExit,
    check_suppressed,
    describe_suppressed,
    is_suppressed,
)


class TestSuppressConfig:
    def test_valid_config_accepted(self):
        cfg = SuppressConfig.from_iterable([1, 2, 3])
        assert cfg.codes == frozenset({1, 2, 3})

    def test_empty_codes_accepted(self):
        cfg = SuppressConfig()
        assert cfg.codes == frozenset()

    def test_non_integer_code_raises(self):
        with pytest.raises(TypeError):
            SuppressConfig(codes=frozenset({"not-an-int"}))  # type: ignore[arg-type]

    def test_from_iterable_deduplicates(self):
        cfg = SuppressConfig.from_iterable([5, 5, 5])
        assert cfg.codes == frozenset({5})

    def test_config_is_hashable(self):
        cfg = SuppressConfig.from_iterable([0, 1])
        assert hash(cfg) is not None


class TestIsSuppressed:
    def setup_method(self):
        self.cfg = SuppressConfig.from_iterable([0, 75, 130])

    def test_suppressed_code_returns_true(self):
        assert is_suppressed(self.cfg, 75) is True

    def test_unsuppressed_code_returns_false(self):
        assert is_suppressed(self.cfg, 1) is False

    def test_zero_suppressed(self):
        assert is_suppressed(self.cfg, 0) is True

    def test_empty_config_never_suppresses(self):
        cfg = SuppressConfig()
        assert is_suppressed(cfg, 1) is False


class TestCheckSuppressed:
    def setup_method(self):
        self.cfg = SuppressConfig.from_iterable([42])

    def test_suppressed_code_raises(self):
        with pytest.raises(SuppressedExit) as exc_info:
            check_suppressed(self.cfg, 42)
        assert exc_info.value.code == 42

    def test_unsuppressed_code_does_not_raise(self):
        check_suppressed(self.cfg, 1)  # should not raise

    def test_suppressed_exit_str(self):
        exc = SuppressedExit(99)
        assert "99" in str(exc)


class TestDescribeSuppressed:
    def test_empty_config_message(self):
        cfg = SuppressConfig()
        assert describe_suppressed(cfg) == "no exit codes suppressed"

    def test_single_code_listed(self):
        cfg = SuppressConfig.from_iterable([7])
        result = describe_suppressed(cfg)
        assert "7" in result

    def test_codes_are_sorted(self):
        cfg = SuppressConfig.from_iterable([10, 3, 7])
        result = describe_suppressed(cfg)
        assert result == "suppressed exit codes: 3, 7, 10"
