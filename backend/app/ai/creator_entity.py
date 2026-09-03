"""Deterministic creator-entity classification from observable channel text.

Used to reject organization/show/label channels before ranking. Generic
indicators only — never a name blacklist.
"""

from __future__ import annotations

from typing import Iterable, Optional, Tuple

INDIVIDUAL_CREATOR = "INDIVIDUAL_CREATOR"
CREATOR_LED_CHANNEL = "CREATOR_LED_CHANNEL"
TEAM_CREATOR_CHANNEL = "TEAM_CREATOR_CHANNEL"
BRAND = "BRAND"
COMPANY = "COMPANY"
TV_NETWORK = "TV_NETWORK"
SHOW = "SHOW"
MEDIA_NETWORK = "MEDIA_NETWORK"
MUSIC_LABEL = "MUSIC_LABEL"
NEWS_ORGANIZATION = "NEWS_ORGANIZATION"
AGGREGATOR = "AGGREGATOR"
INSTITUTION = "INSTITUTION"
OTHER_ORGANIZATION = "OTHER_ORGANIZATION"

COLLABORABLE_ENTITIES = frozenset({INDIVIDUAL_CREATOR, CREATOR_LED_CHANNEL})
ORGANIZATION_ENTITIES = frozenset(
    {
        TEAM_CREATOR_CHANNEL,
        BRAND,
        COMPANY,
        TV_NETWORK,
        SHOW,
        MEDIA_NETWORK,
        MUSIC_LABEL,
        NEWS_ORGANIZATION,
        AGGREGATOR,
        INSTITUTION,
        OTHER_ORGANIZATION,
    }
)

_ORG_TYPE_HINTS = (
    (MUSIC_LABEL, ("record label", "music label", "official music", "film songs", "music company")),
    (NEWS_ORGANIZATION, ("news channel", "breaking news", "news organization", "news network")),
    (TV_NETWORK, ("tv network", "television network", "broadcast network")),
    (SHOW, ("tv show", "television show", "full episode", "reality show", "watch the show")),
    (MEDIA_NETWORK, ("media group", "media network", "entertainment network", "digital network")),
    (INSTITUTION, ("university official", "ministry of", "government of", "official institute")),
    (AGGREGATOR, ("best of compilation", "top 10 songs", "non stop hits")),
    (COMPANY, ("pvt ltd", "private limited", "inc.", "llc", "corporation", "official brand")),
    (BRAND, ("brand channel", "corporate channel")),
    (TEAM_CREATOR_CHANNEL, (
        "our team",
        "team of chefs",
        "recipe network",
        "food network",
        "cooking crew",
        "our kitchen team",
        "village cooking",
        "community kitchen",
        "cooking team",
        "village kitchen",
        "village recipe",
        "we are a team",
        "our crew",
        "group of chefs",
    )),
)

_ORG_TERMS = (
    "official network",
    "tv network",
    "television network",
    "television show",
    "media group",
    "media network",
    "record label",
    "music label",
    "film studio",
    "news channel",
    "news organization",
    "channel network",
    "streaming service",
    "pvt ltd",
    "private limited",
    "corporation",
    "full episode",
    "reality show",
    "official brand",
    "corporate channel",
    "our team",
    "team of chefs",
    "recipe network",
    "food network",
    "cooking crew",
    "village cooking",
    "community kitchen",
    "cooking team",
    "village kitchen",
    "village recipe",
    "we are a team",
    "our crew",
    "group of chefs",
)
_CREATOR_TERMS = (
    "i am",
    "i'm",
    "my channel",
    "subscribe to me",
    "daily vlog",
    "personal",
    "creator",
    "youtuber",
)

_RURAL_NICHE_TERMS = (
    "village",
    "rural",
    "farming",
    "agriculture",
    "kisan",
    "sattvik",
    "satvik",
    "traditional recipe",
    "village food",
    "gaon",
)


def _blob(name: Optional[str], description: Optional[str], titles: Optional[Iterable[str]]) -> str:
    parts = [str(name or ""), str(description or "")]
    for title in titles or []:
        parts.append(str(title or ""))
    return " ".join(parts).lower()


def _is_collective_property(text: str, creator_hits: int) -> bool:
    """Group/property channels, detected from observable language — not a name blacklist."""
    if creator_hits > 0:
        return False
    cooking = any(token in text for token in ("cook", "recipe", "kitchen", "chef"))
    collective = any(
        token in text
        for token in ("village", "team", "community", "our crew", "group of", "we are a")
    )
    return cooking and collective


def classify_creator_entity(
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    recent_titles: Optional[Iterable[str]] = None,
) -> Tuple[str, int]:
    """Return (entity_type, organization_signal_count)."""
    text = _blob(name, description, recent_titles)
    org_hits = sum(1 for term in _ORG_TERMS if term in text)
    creator_hits = sum(1 for term in _CREATOR_TERMS if term in text)
    if _is_collective_property(text, creator_hits):
        org_hits = max(org_hits, 1)
        return TEAM_CREATOR_CHANNEL, org_hits

    detected = OTHER_ORGANIZATION if org_hits else INDIVIDUAL_CREATOR
    for entity, hints in _ORG_TYPE_HINTS:
        if any(hint in text for hint in hints):
            detected = entity
            break

    if org_hits >= 2 and creator_hits == 0:
        return detected if detected in ORGANIZATION_ENTITIES else OTHER_ORGANIZATION, org_hits
    if org_hits >= 2 and detected in ORGANIZATION_ENTITIES:
        return detected, org_hits
    if creator_hits >= 1 and org_hits <= 1:
        return (CREATOR_LED_CHANNEL if "official" in text else INDIVIDUAL_CREATOR), org_hits
    if org_hits >= 1 and creator_hits == 0 and detected in ORGANIZATION_ENTITIES:
        return detected, org_hits
    return INDIVIDUAL_CREATOR, org_hits


def is_collaborable_entity(entity_type: Optional[str]) -> bool:
    return str(entity_type or "").upper() in COLLABORABLE_ENTITIES


def has_single_creator_authority(entity_type: Optional[str]) -> bool:
    return str(entity_type or "").upper() in COLLABORABLE_ENTITIES


def rural_persona_mismatch_score(*, name: Optional[str], description: Optional[str], recent_titles: Optional[Iterable[str]] = None) -> int:
    text = _blob(name, description, recent_titles)
    return sum(1 for term in _RURAL_NICHE_TERMS if term in text)
