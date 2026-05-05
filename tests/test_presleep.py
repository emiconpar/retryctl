"""Tests for retryctl.presleep."""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from retryctl.presleep import (
    PreSleepConfig,
    PreSleepExpired,
    apply_presleep,
    attach_presleep_hook,
)


# ---------------------------------------------------------------------------
# PreSleepConfig validation
# ---------------------------------------------------------------------------

class TestPreSleepConfig:
    def test_valid_config_accepted(self) -> None:
        cfg = PreSleepConfig(duration=1.5)
        assert cfg.duration == 1.5

    def test_zero_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            PreSleepConfig(duration=0)

    def test_negative_duration_raises(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            PreSleepConfig(duration=-3.0)


# ---------------------------------------------------------------------------
# PreSleepExpired
# ---------------------------------------------------------------------------

class TestPreSleepExpired:
    def test_stores_duration(self) -> None:
        exc = PreSleepExpired(2.5)
        assert exc.duration == 2.5

    def test_message_contains_duration(self) -> None:
        exc = PreSleepExpired(2.5)
        assert "2.5" in str(exc)


# ---------------------------------------------------------------------------
# apply_presleep
# ---------------------------------------------------------------------------

class TestApplyPresleep:
    def test_sleeps_for_configured_duration(self) -> None:
        mock_sleep = MagicMock()
        apply_presleep(PreSleepConfig(duration=3.0), _sleep=mock_sleep)
        mock_sleep.assert_called_once_with(3.0)

    def test_sleeps_fractional_seconds(self) -> None:
        mock_sleep = MagicMock()
        apply_presleep(PreSleepConfig(duration=0.25), _sleep=mock_sleep)
        mock_sleep.assert_called_once_with(0.25)


# ---------------------------------------------------------------------------
# attach_presleep_hook
# ---------------------------------------------------------------------------

class TestAttachPresleepHook:
    def _make_registry(self) -> MagicMock:
        registry = MagicMock()
        registry._on_retry_hooks: list = []

        def _register(fn):
            registry._on_retry_hooks.append(fn)

        registry.register_on_retry.side_effect = _register
        return registry

    def test_registers_on_retry_hook(self) -> None:
        registry = self._make_registry()
        attach_presleep_hook(registry, PreSleepConfig(duration=1.0))
        registry.register_on_retry.assert_called_once()

    def test_hook_sleeps_on_first_call(self) -> None:
        mock_sleep = MagicMock()
        registry = self._make_registry()
        attach_presleep_hook(
            registry, PreSleepConfig(duration=2.0), _sleep=mock_sleep
        )
        hook = registry._on_retry_hooks[0]
        hook(ctx=object())
        mock_sleep.assert_called_once_with(2.0)

    def test_hook_does_not_sleep_on_subsequent_calls(self) -> None:
        mock_sleep = MagicMock()
        registry = self._make_registry()
        attach_presleep_hook(
            registry, PreSleepConfig(duration=2.0), _sleep=mock_sleep
        )
        hook = registry._on_retry_hooks[0]
        hook(ctx=object())
        hook(ctx=object())
        hook(ctx=object())
        assert mock_sleep.call_count == 1
