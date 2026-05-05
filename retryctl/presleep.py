"""Pre-sleep hook: pause before the first attempt if configured."""
from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class PreSleepConfig:
    """Configuration for a mandatory delay before the first attempt."""

    duration: float  # seconds

    def __post_init__(self) -> None:
        if self.duration <= 0:
            raise ValueError(
                f"PreSleepConfig.duration must be positive, got {self.duration}"
            )


class PreSleepExpired(Exception):
    """Raised when pre-sleep is interrupted (reserved for future use)."""

    def __init__(self, duration: float) -> None:
        super().__init__(f"Pre-sleep of {duration}s was interrupted")
        self.duration = duration


def apply_presleep(
    config: PreSleepConfig,
    *,
    _sleep: "Callable[[float], None]" = time.sleep,  # injectable for tests
) -> None:
    """Block for *config.duration* seconds before the first attempt."""
    _sleep(config.duration)


def attach_presleep_hook(
    registry: "HookRegistry",  # type: ignore[name-defined]  # noqa: F821
    config: PreSleepConfig,
    *,
    _sleep: "Callable[[float], None]" = time.sleep,
) -> None:
    """Register a one-shot pre-sleep that fires before the very first attempt.

    The hook self-removes after the first invocation so subsequent retries are
    not delayed by the pre-sleep again.
    """
    fired: list[bool] = [False]

    def _on_before_attempt(ctx: object, **_kwargs: object) -> None:  # noqa: ANN001
        if not fired[0]:
            fired[0] = True
            apply_presleep(config, _sleep=_sleep)

    registry.register_on_retry(_on_before_attempt)
