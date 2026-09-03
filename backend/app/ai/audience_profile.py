"""Normalize campaign target persona / age-group from real campaign fields.

Never invent demographic percentages. Explicit numeric age ranges outrank
inferred named terms when they clearly contradict each other.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

PERSONA_GEN_Z = "GEN_Z"
PERSONA_ADULT = "ADULT"
PERSONA_MATURE = "MATURE_AUDIENCE"
PERSONA_UNKNOWN = "UNKNOWN"

_GEN_Z_TERMS = (
    "gen z",
    "genz",
    "gen-z",
    "youth",
    "young adult",
    "college",
    "campus",
    "teen",
    "18-24",
    "18–24",
    "18-27",
    "gaming audience",
    "young lifestyle",
)
_ADULT_TERMS = (
    "working professional",
    "professionals",
    "parents",
    "parenting",
    "adults",
    "30-45",
    "30–45",
    "35-50",
    "35–50",
    "35-55",
    "career",
)
_MATURE_TERMS = (
    "older adult",
    "senior",
    "50+",
    "55+",
    "mature audience",
    "retirement",
)


@dataclass(frozen=True)
class AudienceProfile:
    persona: str
    age_min: Optional[int]
    age_max: Optional[int]
    source: str
    terms: Tuple[str, ...]


def _as_int(value: Any) -> Optional[int]:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _blob(*parts: Any) -> str:
    chunks: List[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, (list, tuple, set)):
            chunks.extend(str(x) for x in part if x)
        else:
            chunks.append(str(part))
    return " ".join(chunks).lower()


def _named_persona(text: str) -> str:
    if any(term in text for term in _GEN_Z_TERMS):
        return PERSONA_GEN_Z
    if any(term in text for term in _MATURE_TERMS):
        return PERSONA_MATURE
    if any(term in text for term in _ADULT_TERMS):
        return PERSONA_ADULT
    return PERSONA_UNKNOWN


def _persona_from_ages(age_min: Optional[int], age_max: Optional[int]) -> str:
    if age_min is None and age_max is None:
        return PERSONA_UNKNOWN
    lo = age_min if age_min is not None else 0
    hi = age_max if age_max is not None else 100
    if hi <= 27 or (lo <= 24 and hi <= 34):
        return PERSONA_GEN_Z
    if lo >= 50 or (lo >= 45 and hi >= 55):
        return PERSONA_MATURE
    if lo >= 30 or (hi >= 40 and lo >= 25):
        return PERSONA_ADULT
    return PERSONA_UNKNOWN


def build_audience_profile(
    *,
    description: Optional[str] = None,
    interests: Optional[List[Any]] = None,
    objective: Optional[str] = None,
    target_age_min: Any = None,
    target_age_max: Any = None,
    extra_text: Optional[str] = None,
) -> AudienceProfile:
    age_min = _as_int(target_age_min)
    age_max = _as_int(target_age_max)
    text = _blob(description, interests, objective, extra_text)
    named = _named_persona(text)
    from_ages = _persona_from_ages(age_min, age_max)

    if from_ages != PERSONA_UNKNOWN and named != PERSONA_UNKNOWN and from_ages != named:
        if age_min is not None and age_max is not None and (age_max - age_min) <= 25:
            persona = from_ages
            source = "USER_AGE_RANGE"
        else:
            persona = named
            source = "NAMED_AUDIENCE"
    elif named != PERSONA_UNKNOWN:
        persona = named
        source = "NAMED_AUDIENCE"
    elif from_ages != PERSONA_UNKNOWN:
        persona = from_ages
        source = "USER_AGE_RANGE"
    else:
        persona = PERSONA_UNKNOWN
        source = "UNKNOWN"

    found: List[str] = []
    for term in _GEN_Z_TERMS + _ADULT_TERMS + _MATURE_TERMS:
        if term in text and term not in found:
            found.append(term)
    return AudienceProfile(
        persona=persona,
        age_min=age_min,
        age_max=age_max,
        source=source,
        terms=tuple(found[:8]),
    )


def is_awareness_objective(objective: Optional[str]) -> bool:
    blob = str(objective or "").lower()
    return any(token in blob for token in ("awareness", "reach", "brand"))
