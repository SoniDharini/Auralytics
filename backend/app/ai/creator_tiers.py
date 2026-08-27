"""Configurable creator-tier follower ranges used by Strategy and Discovery.

These are recommendation thresholds — not creator pricing or fee estimates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class CreatorTierRange:
    key: str
    label: str
    minimum: int
    maximum: Optional[int]  # None = open-ended (mega)


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


def normalize_tier_key(raw: str) -> str:
    text = (raw or "").strip().lower()
    if not text:
        return ""
    # Accept labels like "Micro (10k-100k)" or "MID_TIER".
    for key in CREATOR_TIER_RANGES:
        if key.replace("_", "-") in text.replace("_", "-") or key in text:
            return key if key in CREATOR_TIER_RANGES else text
    if "nano" in text:
        return "nano"
    if "micro" in text:
        return "micro"
    if "mid" in text:
        return "mid"
    if "macro" in text:
        return "macro"
    if "mega" in text or "celebrity" in text:
        return "mega"
    return text


def tier_for_followers(followers: int) -> str:
    if followers < 1_000:
        return "nano"
    if followers < 10_000:
        return "nano"
    if followers < 100_000:
        return "micro"
    if followers < 500_000:
        return "mid"
    if followers < 1_000_000:
        return "macro"
    return "mega"


def range_for_tiers(tiers: Iterable[str]) -> Tuple[Optional[int], Optional[int]]:
    """Union follower range across preferred tiers. Returns (min, max)."""
    mins: List[int] = []
    maxs: List[Optional[int]] = []
    for raw in tiers:
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
            # Alias mid variants together for matching.
            if key in {"mid", "mid_tier", "mid-tier"}:
                keys.update({"mid", "mid_tier", "mid-tier"})
    return keys
