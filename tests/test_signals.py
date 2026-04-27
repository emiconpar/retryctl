"""Tests for retryctl.signals module."""

from __future__ import annotations

import signal
import pytest

from retryctl.signals import (
    SignalInfo,
    exit_code_from_returncode,
    should_retry_on_signal,
)


class TestSignalInfo:
    def test_from_known_signum(self):
        info = SignalInfo.from_signum(signal.SIGTERM)
        assert info.signum == signal.SIGTERM
        assert info.name == "SIGTERM"

    def test_from_unknown_signum(self):
        info = SignalInfo.from_signum(99)
        assert info.signum == 99
        assert info.name == "SIG99"
        assert info.is_fatal is False

    def test_fatal_signals_marked_correctly(self):
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGKILL):
            info = SignalInfo.from_signum(signum)
            assert info.is_fatal is True, f"{info.name} should be fatal"

    def test_non_fatal_signal(self):
        info = SignalInfo.from_signum(signal.SIGUSR1)
        assert info.is_fatal is False


class TestExitCodeFromReturncode:
    def test_normal_exit_zero(self):
        code, sig_info = exit_code_from_returncode(0)
        assert code == 0
        assert sig_info is None

    def test_normal_exit_nonzero(self):
        code, sig_info = exit_code_from_returncode(1)
        assert code == 1
        assert sig_info is None

    def test_signal_exit_sigterm(self):
        code, sig_info = exit_code_from_returncode(-signal.SIGTERM)
        assert code == 128 + signal.SIGTERM
        assert sig_info is not None
        assert sig_info.signum == signal.SIGTERM

    def test_signal_exit_sigkill(self):
        code, sig_info = exit_code_from_returncode(-signal.SIGKILL)
        assert code == 128 + signal.SIGKILL
        assert sig_info is not None
        assert sig_info.is_fatal is True

    def test_signal_exit_sigusr1(self):
        code, sig_info = exit_code_from_returncode(-signal.SIGUSR1)
        assert sig_info is not None
        assert sig_info.is_fatal is False


class TestShouldRetryOnSignal:
    def test_no_signal_returns_false(self):
        assert should_retry_on_signal(None, retry_on_signals=True) is False

    def test_fatal_signal_never_retries(self):
        info = SignalInfo.from_signum(signal.SIGTERM)
        assert should_retry_on_signal(info, retry_on_signals=True) is False

    def test_non_fatal_signal_retries_when_enabled(self):
        info = SignalInfo.from_signum(signal.SIGUSR1)
        assert should_retry_on_signal(info, retry_on_signals=True) is True

    def test_non_fatal_signal_no_retry_when_disabled(self):
        info = SignalInfo.from_signum(signal.SIGUSR1)
        assert should_retry_on_signal(info, retry_on_signals=False) is False
