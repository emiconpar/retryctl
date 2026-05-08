"""Environment variable masking for subprocess execution.

Allows selectively hiding or overriding environment variables passed
to the child process, preventing secrets from leaking into retried commands.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class EnvMaskConfig:
    """Configuration for environment variable masking."""

    # Variables to remove entirely from the child environment
    remove: List[str] = field(default_factory=list)
    # Variables to override with specific values
    override: Dict[str, str] = field(default_factory=dict)
    # If True, start from an empty environment instead of inheriting
    clean: bool = False

    def __post_init__(self) -> None:
        for key in self.remove:
            if not key or not key.strip():
                raise ValueError("remove entries must be non-blank strings")
        for key in self.override:
            if not key or not key.strip():
                raise ValueError("override keys must be non-blank strings")


def build_env(config: Optional[EnvMaskConfig]) -> Optional[Dict[str, str]]:
    """Build the environment dict to pass to subprocess.

    Returns None when no masking is configured, which tells subprocess
    to inherit the parent environment unchanged.

    Args:
        config: Masking configuration, or None for no masking.

    Returns:
        A new environment dict, or None if config is None.
    """
    if config is None:
        return None

    base: Dict[str, str] = {} if config.clean else dict(os.environ)

    for key in config.remove:
        base.pop(key, None)

    base.update(config.override)

    return base


def describe_mask(config: EnvMaskConfig) -> str:
    """Return a human-readable summary of the masking config."""
    parts: List[str] = []
    if config.clean:
        parts.append("clean=True")
    if config.remove:
        parts.append(f"remove={config.remove}")
    if config.override:
        keys = list(config.override.keys())
        parts.append(f"override_keys={keys}")
    if not parts:
        return "EnvMaskConfig(no-op)"
    return "EnvMaskConfig(" + ", ".join(parts) + ")"
