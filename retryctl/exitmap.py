"""Exit code mapping: translate raw exit codes into semantic labels."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class ExitMapConfig:
    """Configuration for exit code label mapping."""

    mapping: Dict[int, str] = field(default_factory=dict)
    default_label: str = "unknown"

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, dict):
            raise TypeError("mapping must be a dict")
        for code, label in self.mapping.items():
            if not isinstance(code, int):
                raise TypeError(f"exit code key must be int, got {type(code).__name__!r}")
            if not isinstance(label, str) or not label.strip():
                raise ValueError(f"label for code {code} must be a non-blank string")
        if not isinstance(self.default_label, str) or not self.default_label.strip():
            raise ValueError("default_label must be a non-blank string")


@dataclass
class ExitCodeLabel:
    """Result of a label lookup."""

    code: int
    label: str
    is_default: bool

    def to_dict(self) -> dict:
        return {"code": self.code, "label": self.label, "is_default": self.is_default}


class ExitMapper:
    """Maps exit codes to human-readable labels."""

    def __init__(self, config: ExitMapConfig) -> None:
        self._config = config

    def lookup(self, code: int) -> ExitCodeLabel:
        """Return the label for *code*, falling back to the default label."""
        if code in self._config.mapping:
            return ExitCodeLabel(
                code=code,
                label=self._config.mapping[code],
                is_default=False,
            )
        return ExitCodeLabel(
            code=code,
            label=self._config.default_label,
            is_default=True,
        )

    def known_codes(self) -> Dict[int, str]:
        """Return a copy of the configured code-to-label mapping."""
        return dict(self._config.mapping)

    def describe(self) -> str:
        """Return a human-readable summary of the mapping."""
        if not self._config.mapping:
            return f"ExitMapper(default={self._config.default_label!r}, no explicit mappings)"
        pairs = ", ".join(f"{c}={l!r}" for c, l in sorted(self._config.mapping.items()))
        return f"ExitMapper(default={self._config.default_label!r}, {pairs})"

    def lookup_many(self, codes: list[int]) -> Dict[int, ExitCodeLabel]:
        """Look up labels for multiple exit codes at once.

        Args:
            codes: A list of exit codes to resolve.

        Returns:
            A dict mapping each code to its :class:`ExitCodeLabel`.
        """
        return {code: self.lookup(code) for code in codes}
