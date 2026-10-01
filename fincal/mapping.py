"""Resolve spending log items to categories and categories to budget buckets."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

UNMAPPED = "Unmapped"

_WS = re.compile(r"\s+")


def normalize(value: object) -> str:
    if value is None:
        return ""
    return _WS.sub(" ", str(value)).strip().casefold()


@dataclass
class Lookup:
    """Case/whitespace-insensitive lookup with longest-substring fallback."""

    exact: dict[str, str] = field(default_factory=dict)
    conflicts: dict[str, set[str]] = field(default_factory=dict)
    _by_length: list[str] = field(default_factory=list)

    @classmethod
    def from_pairs(cls, pairs) -> Lookup:
        lookup = cls()
        for key, value in pairs:
            norm = normalize(key)
            if not norm or value is None or str(value).strip() == "":
                continue
            value = str(value).strip()
            existing = lookup.exact.get(norm)
            if existing is not None and existing != value:
                lookup.conflicts.setdefault(norm, {existing}).add(value)
                continue  # first one wins
            lookup.exact[norm] = value
        lookup._by_length = sorted(lookup.exact, key=len, reverse=True)
        return lookup

    @classmethod
    def from_dict(cls, mapping: dict[str, str]) -> Lookup:
        return cls.from_pairs(mapping.items())

    def match(self, key: object, substring: bool = True) -> str | None:
        """The normalized mapping key that ``key`` resolves through, if any."""
        norm = normalize(key)
        if not norm:
            return None
        if norm in self.exact:
            return norm
        if substring:
            return next((c for c in self._by_length if c in norm), None)
        return None

    def get(self, key: object, substring: bool = True) -> str | None:
        matched = self.match(key, substring)
        return None if matched is None else self.exact[matched]


def resolve_category(item: object, items: Lookup) -> str:
    return items.get(item) or UNMAPPED


def resolve_bucket(category: object, categories: Lookup) -> str:
    return categories.get(category, substring=False) or UNMAPPED
