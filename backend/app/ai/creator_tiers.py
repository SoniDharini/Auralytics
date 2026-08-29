"""Configurable creator-tier follower ranges used by Strategy and Discovery.

These are recommendation thresholds — not creator pricing or fee estimates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class CreatorTierRange:
    key: str
    label: str
    minimum: int
    maximum: Optional[int]  # None = open-ended (mega / celebrity)


# Central thresholds — keep Strategy and Discovery aligned.
CREATOR_TIER_RANGES: Dict[str, CreatorTierRange] = {
    "nano": CreatorTierRange("nano", "Nano", 1_000, 10_000),
    "micro": CreatorTierRange("micro", "Micro", 10_000, 100_000),
    "mid": CreatorTierRange("mid", "Mid-Tier", 100_000, 500_000),
    "mid_tier": CreatorTierRange("mid_tier", "Mid-Tier", 100_000, 500_000),
    "mid-tier": CreatorTierRange("mid-tier", "Mid-Tier", 100_000, 500_000),
    "macro": CreatorTierRange("macro", "Macro", 500_000, 1_000_000),
    "mega": CreatorTierRange("mega", "Mega", 1_000_000, None),
    "celebrity": CreatorTierRange("celebrity", "Celebrity", 1_000_000, None),
}

# Canonical families so aliases compare equal (mid-tier == mid, celebrity == mega).
TIER_FAMILIES: Dict[str, str] = {
    "nano": "nano",
    "micro": "micro",
    "mid": "mid",
    "mid_tier": "mid",
    "mid-tier": "mid",
    "macro": "macro",
    "mega": "mega",
    "celebrity": "mega",
}

# Prefer the user-facing key when stamping strategy output.
FAMILY_DISPLAY_KEY: Dict[str, str] = {
    "nano": "nano",
    "micro": "micro",
    "mid": "mid-tier",
    "macro": "macro",
    "mega": "celebrity",
}


def normalize_tier_key(raw: str) -> str:
    text = (raw or "").strip().lower()
    if not text:
        return ""
    # Longer keys first so "mid-tier" wins over "mid" and "celebrity" over "cele".
    for key in sorted(CREATOR_TIER_RANGES, key=len, reverse=True):
        needle = key.replace("_", "-")
        haystack = text.replace("_", "-")
        if needle in haystack or key in text:
            return key
    if "nano" in text:
        return "nano"
    if "micro" in text:
        return "micro"
    if "mid" in text:
        return "mid"
    if "macro" in text:
        return "macro"
    if "mega" in text or "celebrity" in text:
        return "celebrity"
    return text


def canonical_tier_family(raw: str) -> str:
    key = normalize_tier_key(raw)
    return TIER_FAMILIES.get(key, key)


def display_tier_key(raw: str) -> str:
    family = canonical_tier_family(raw)
    return FAMILY_DISPLAY_KEY.get(family, family or (raw or "").strip().lower())


def tier_for_followers(followers: int) -> str:
    if followers < 10_000:
        return "nano"
    if followers < 100_000:
        return "micro"
    if followers < 500_000:
        return "mid"
    if followers < 1_000_000:
        return "macro"
    return "mega"


def selected_tier_keys(raw_tiers: Optional[Iterable[Any]]) -> List[str]:
    """Preserve first-seen user order; collapse aliases into display keys."""
    ordered: List[str] = []
    seen: Set[str] = set()
    if not raw_tiers:
        return ordered
    for raw in raw_tiers:
        if raw is None:
            continue
        display = display_tier_key(str(raw))
        family = canonical_tier_family(display)
        if not family or family in seen:
            continue
        seen.add(family)
        ordered.append(display)
    return ordered


def selected_tier_families(raw_tiers: Optional[Iterable[Any]]) -> Set[str]:
    return {canonical_tier_family(k) for k in selected_tier_keys(raw_tiers) if k}


def subscriber_ranges_for_tiers(tiers: Optional[Iterable[Any]]) -> List[Dict[str, Any]]:
    ranges: List[Dict[str, Any]] = []
    for key in selected_tier_keys(tiers):
        spec = CREATOR_TIER_RANGES.get(normalize_tier_key(key))
        if not spec:
            continue
        ranges.append(
            {
                "tier": key,
                "min": spec.minimum,
                "max": spec.maximum,
            }
        )
    return ranges


def range_for_tiers(tiers: Iterable[str]) -> Tuple[Optional[int], Optional[int]]:
    """Union follower range across preferred tiers. Returns (min, max).

    The union can include gaps (e.g. MICRO + MACRO spans mid-tier numerically).
    Hard eligibility must use followers_match_selected_tiers, not this union.
    """
    mins: List[int] = []
    maxs: List[Optional[int]] = []
    for raw in selected_tier_keys(list(tiers) if not isinstance(tiers, list) else tiers) or list(tiers):
        key = normalize_tier_key(raw if isinstance(raw, str) else str(raw))
        tier = CREATOR_TIER_RANGES.get(key)
        if not tier:
            continue
        mins.append(tier.minimum)
        maxs.append(tier.maximum)
    if not mins:
        return None, None
    overall_min = min(mins)
    if any(m is None for m in maxs):
        return overall_min, None
    return overall_min, max(m for m in maxs if m is not None)


def followers_match_range(
    followers: int,
    *,
    minimum: Optional[int],
    maximum: Optional[int],
    hidden: bool = False,
) -> bool:
    """Hidden/unknown subscriber counts are kept (missing info ≠ disqualification)."""
    if hidden or followers <= 0:
        return True
    if minimum is not None and followers < minimum:
        return False
    if maximum is not None and followers > maximum:
        return False
    return True


def followers_match_selected_tiers(
    followers: int,
    tiers: Optional[Iterable[Any]],
    *,
    hidden: bool = False,
) -> bool:
    """True when the creator falls in at least one selected tier range.

    Gaps between selected tiers (e.g. mid-tier when MICRO+MACRO are selected)
    are not eligible.
    """
    families = selected_tier_families(tiers)
    if not families:
        return True
    if hidden or followers <= 0:
        return True
    return canonical_tier_family(tier_for_followers(followers)) in families


def ranges_meaningfully_overlap(
    a_min: Optional[int],
    a_max: Optional[int],
    b_min: Optional[int],
    b_max: Optional[int],
) -> bool:
    """True when two ranges share more than a single boundary point."""
    lo = max(a_min or 0, b_min or 0)
    if a_max is None and b_max is None:
        return True
    if a_max is None:
        return b_max is None or lo < b_max
    if b_max is None:
        return lo < a_max
    return lo < min(a_max, b_max)


def campaign_min_max_compatible_with_tiers(
    raw_tiers: Optional[Iterable[Any]],
    user_min: Optional[int],
    user_max: Optional[int],
) -> bool:
    """Whether campaign min/max can tighten selected tiers without wiping them out.

    Form defaults of 10K–500K must not erase a MACRO + CELEBRITY selection.
    """
    if user_min is None and user_max is None:
        return False
    specs = subscriber_ranges_for_tiers(raw_tiers)
    if not specs:
        return True
    for spec in specs:
        if ranges_meaningfully_overlap(spec.get("min"), spec.get("max"), user_min, user_max):
            return True
    return False


def extract_subscriber_range(strategy_json: Optional[Dict]) -> Tuple[Optional[int], Optional[int]]:
    """Resolve recommended subscriber range from persisted strategy."""
    if not strategy_json:
        return None, None
    creator = strategy_json.get("creator_strategy") or {}
    rng = creator.get("recommended_subscriber_range") or strategy_json.get(
        "recommended_subscriber_range"
    )
    if isinstance(rng, dict):
        try:
            mn = int(rng["minimum"]) if rng.get("minimum") is not None else None
        except (TypeError, ValueError):
            mn = None
        try:
            mx = int(rng["maximum"]) if rng.get("maximum") is not None else None
        except (TypeError, ValueError):
            mx = None
        if mn is not None or mx is not None:
            return mn, mx

    tiers: List[str] = []
    for item in creator.get("preferred_creator_tiers") or []:
        if isinstance(item, dict) and item.get("tier"):
            tiers.append(str(item["tier"]))
        elif isinstance(item, str):
            tiers.append(item)
    for item in strategy_json.get("creator_tier_strategy") or []:
        if isinstance(item, dict) and item.get("tier"):
            tiers.append(str(item["tier"]))
    stamped = strategy_json.get("user_selected_creator_tiers") or []
    if stamped:
        tiers = list(stamped) + tiers
    return range_for_tiers(tiers)


def preferred_tier_keys(strategy_json: Optional[Dict]) -> Set[str]:
    if not strategy_json:
        return set()
    creator = strategy_json.get("creator_strategy") or {}
    keys: Set[str] = set()
    for item in creator.get("preferred_creator_tiers") or []:
        raw = item.get("tier") if isinstance(item, dict) else item
        key = normalize_tier_key(str(raw or ""))
        if key:
            keys.add(key)
            family = canonical_tier_family(key)
            if family == "mid":
                keys.update({"mid", "mid_tier", "mid-tier"})
            if family == "mega":
                keys.update({"mega", "celebrity"})
    return keys
