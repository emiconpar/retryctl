"""Hook integration for the Watchdog feature."""
from __future__ import annotations

from retryctl.hooks import HookRegistry
from retryctl.watchdog import Watchdog, WatchdogConfig, WatchdogTripped


def attach_watchdog_hooks(
    registry: HookRegistry,
    config: WatchdogConfig,
) -> Watchdog:
    """Create a Watchdog and wire it into the hook registry.

    The watchdog is:
    - Started on each retry attempt (on_retry)
    - Stopped cleanly on final failure or success

    Returns the Watchdog instance so callers can call `.feed()` during
    long-running subprocess polling loops.
    """
    tripped_events: list[tuple[str, float]] = []

    def _on_trip(key: str, stall_timeout: float) -> None:
        tripped_events.append((key, stall_timeout))

    watchdog = Watchdog(config=config, on_trip=_on_trip)

    def _on_retry(result, ctx) -> None:  # type: ignore[type-arg]
        watchdog.start()

    def _on_attempt_failure(result, ctx) -> None:  # type: ignore[type-arg]
        watchdog.feed()

    def _on_final_failure(result, ctx) -> None:  # type: ignore[type-arg]
        watchdog.stop()
        if watchdog.tripped:
            raise WatchdogTripped(config.key, config.stall_timeout)

    def _on_success(result, ctx) -> None:  # type: ignore[type-arg]
        watchdog.stop()

    registry.register_on_retry(_on_retry)
    registry.register_on_attempt_failure(_on_attempt_failure)
    registry.register_on_final_failure(_on_final_failure)
    registry.register_on_success(_on_success)

    return watchdog
