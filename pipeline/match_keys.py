"""Name normalization, binomial keys, and name-quality classification."""

from __future__ import annotations

import re
from typing import Literal

from pipeline.schema import normalize_name

NameQuality = Literal["binomial", "trinomial", "hybrid", "placeholder", "informal", "empty"]

_PLACEHOLDER_MARKERS = (
    " sp.",
    " cf.",
    " cf ",
    " aff.",
    " aff ",
    " nr.",
    " nr ",
    "unclassified",
    "uncultured",
    "environmental",
    "unidentified",
    "metagenome",
    "symbiont",
)


def norm_key(name: str | None) -> str:
    return normalize_name(name).lower()


def binom_key(name: str | None) -> str:
    """Author-stripped genus + epithet key for cross-universe matching."""
    n = normalize_name(name)
    if not n:
        return ""
    cleaned = re.sub(r"[^\w\s-]", " ", n)
    parts = cleaned.split()
    if len(parts) < 2:
        return n.lower()
    return f"{parts[0].lower()} {parts[1].lower()}"


def genus_from_name(name: str | None) -> str:
    n = normalize_name(name)
    if not n:
        return ""
    parts = n.split()
    if not parts:
        return ""
    return parts[0].lower()


def name_quality(name: str | None) -> NameQuality:
    n = normalize_name(name)
    if not n:
        return "empty"
    low = n.lower()
    if "×" in n or " x " in low or low.startswith("x "):
        return "hybrid"
    for marker in _PLACEHOLDER_MARKERS:
        if marker in low or (marker.strip() == "sp." and low.endswith(" sp")):
            return "placeholder"
    parts = low.split()
    if len(parts) >= 3 and parts[0][0].isalpha():
        return "trinomial"
    if len(parts) >= 2 and parts[0][0].isalpha():
        if low.endswith(" sp") or " sp." in low:
            return "placeholder"
        return "binomial"
    if len(parts) == 1:
        return "informal"
    return "informal"


def is_resolvable_name(name: str | None) -> bool:
    return name_quality(name) in ("binomial", "trinomial", "hybrid")
