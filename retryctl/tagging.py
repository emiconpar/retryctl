"""Attempt tagging: attach structured tags to each retry attempt for downstream filtering."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class TaggingConfig:
    """Configuration for attempt tagging."""

    static_tags: Dict[str, str] = field(default_factory=dict)
    include_attempt_number: bool = True
    include_exit_code: bool = True
    prefix: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.static_tags, dict):
            raise TypeError("static_tags must be a dict")
        for k, v in self.static_tags.items():
            if not isinstance(k, str) or not k.strip():
                raise ValueError("Tag keys must be non-blank strings")
            if not isinstance(v, str):
                raise TypeError(f"Tag value for '{k}' must be a string")
        if not isinstance(self.prefix, str):
            raise TypeError("prefix must be a string")


@dataclass
class AttemptTags:
    """Resolved tags for a single attempt."""

    tags: Dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> Optional[str]:
        return self.tags.get(key)

    def all(self) -> Dict[str, str]:
        return dict(self.tags)

    def with_tag(self, key: str, value: str) -> "AttemptTags":
        return AttemptTags({**self.tags, key: value})


def build_tags(
    config: TaggingConfig,
    attempt_number: int,
    exit_code: Optional[int] = None,
) -> AttemptTags:
    """Build an AttemptTags instance from config and runtime values."""
    p = config.prefix
    tags: Dict[str, str] = {}

    for k, v in config.static_tags.items():
        tags[f"{p}{k}" if p else k] = v

    if config.include_attempt_number:
        tags[f"{p}attempt" if p else "attempt"] = str(attempt_number)

    if config.include_exit_code and exit_code is not None:
        tags[f"{p}exit_code" if p else "exit_code"] = str(exit_code)

    return AttemptTags(tags)
