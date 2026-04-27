"""Tests for retryctl backoff strategies."""

import pytest
from retryctl.backoff import BackoffConfig, BackoffStrategy, create_backoff


class TestFixedBackoff:
    def test_fixed_delay_is_constant(self):
        cfg = BackoffConfig(strategy=BackoffStrategy.FIXED, base_delay=3.0)
        delays = [cfg.next_delay() for _ in range(5)]
        assert all(d == 3.0 for d in delays)

    def test_fixed_respects_max_delay(self):
        cfg = BackoffConfig(strategy=BackoffStrategy.FIXED, base_delay=100.0, max_delay=10.0)
        assert cfg.next_delay() == 10.0


class TestLinearBackoff:
    def test_linear_increases_linearly(self):
        cfg = BackoffConfig(strategy=BackoffStrategy.LINEAR, base_delay=2.0)
        delays = [cfg.next_delay() for _ in range(4)]
        assert delays == [2.0, 4.0, 6.0, 8.0]

    def test_linear_capped_at_max_delay(self):
        cfg = BackoffConfig(strategy=BackoffStrategy.LINEAR, base_delay=5.0, max_delay=12.0)
        delays = [cfg.next_delay() for _ in range(4)]
        assert delays == [5.0, 10.0, 12.0, 12.0]


class TestExponentialBackoff:
    def test_exponential_growth(self):
        cfg = BackoffConfig(strategy=BackoffStrategy.EXPONENTIAL, base_delay=1.0, multiplier=2.0)
        delays = [cfg.next_delay() for _ in range(4)]
        assert delays == [1.0, 2.0, 4.0, 8.0]

    def test_exponential_capped_at_max_delay(self):
        cfg = BackoffConfig(strategy=BackoffStrategy.EXPONENTIAL, base_delay=1.0,
                            max_delay=5.0, multiplier=2.0)
        delays = [cfg.next_delay() for _ in range(4)]
        assert all(d <= 5.0 for d in delays)

    def test_exponential_jitter_within_bounds(self):
        cfg = BackoffConfig(strategy=BackoffStrategy.EXPONENTIAL_JITTER,
                            base_delay=1.0, multiplier=2.0, max_delay=60.0, jitter_range=0.5)
        for _ in range(50):
            cfg.reset()
            delay = cfg.next_delay()
            assert 0.0 <= delay <= 60.0


class TestReset:
    def test_reset_restarts_sequence(self):
        cfg = BackoffConfig(strategy=BackoffStrategy.EXPONENTIAL, base_delay=1.0, multiplier=2.0)
        first_run = [cfg.next_delay() for _ in range(3)]
        cfg.reset()
        second_run = [cfg.next_delay() for _ in range(3)]
        assert first_run == second_run


class TestCreateBackoff:
    def test_creates_correct_strategy(self):
        cfg = create_backoff("exponential", base_delay=2.0, multiplier=3.0)
        assert cfg.strategy == BackoffStrategy.EXPONENTIAL
        assert cfg.base_delay == 2.0
        assert cfg.multiplier == 3.0

    def test_invalid_strategy_raises(self):
        with pytest.raises(ValueError, match="Unknown strategy"):
            create_backoff("random_walk")
