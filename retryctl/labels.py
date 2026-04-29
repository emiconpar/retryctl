"""Label support for tagging retry runs with arbitrary key-value metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class LabelSet:
    """Immutable collection of string key-value labels attached to a run."""

    _labels: Dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> Optional[str]:
        """Return the value for *key*, or None if not present."""
        return self._labels.get(key)

    def all(self) -> Dict[str, str]:
        """Return a shallow copy of all labels."""
        return dict(self._labels)

    def with_label(self, key: str, value: str) -> "LabelSet":
        """Return a new LabelSet with the given label added or overwritten."""
        if not key:
            raise ValueError("Label key must not be empty")
        updated = dict(self._labels)
        updated[key] = value
        return LabelSet(updated)

    def merge(self, other: "LabelSet") -> "LabelSet":
        """Return a new LabelSet combining both sets; *other* wins on conflict."""
        merged = {**self._labels, **other._labels}
        return LabelSet(merged)

    def __len__(self) -> int:
        return len(self._labels)

    def __contains__(self, key: str) -> bool:
        return key in self._labels

    def __repr__(self) -> str:  # pragma: no cover
        return f"LabelSet({self._labels!r})"


def parse_labels(raw: list[str]) -> LabelSet:
    """Parse a list of 'key=value' strings into a LabelSet.

    Raises ValueError for entries that do not contain '='.
    """
    labels: Dict[str, str] = {}
    for entry in raw:
        if "=" not in entry:
            raise ValueError(
                f"Invalid label {entry!r}: expected 'key=value' format"
            )
        key, _, value = entry.partition("=")
        if not key:
            raise ValueError(f"Label key must not be empty in {entry!r}")
        labels[key] = value
    return LabelSet(labels)
