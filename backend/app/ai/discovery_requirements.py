"""Normalized Discovery requirements: hard user constraints vs Strategy preferences.

User requirements always outrank Strategy Agent recommendations.
This module does not invent campaign facts and does not call Groq.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.ai.creator_tiers import (
    campaign_min_max_compatible_with_tiers,
    extract_subscriber_range,
    followers_match_selected_tiers,
    preferred_tier_keys,
    selected_tier_keys,
    subscriber_ranges_for_tiers,
)
from app.models.campaign import Campaign


def terms_match_text(haystack: str, terms: List[str]) -> Optional[bool]:
    """True if any campaign niche/keyword appears in real creator text."""
    if not terms:
        return None
    blob = (haystack or "").lower()
    if not blob.strip():
        return False
    for raw in terms:
        term = str(raw or "").strip().lower()
        if len(term) < 3:
            continue
        if term in blob:
            return True
        for token in term.replace("-", " ").split():
            if len(token) >= 4 and token in blob:
                return True
    return False


def _as_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        for key in ("niche", "name", "label", "content_type", "factor", "tier"):
            if value.get(key):
                return _as_str_list(value.get(key))
        return []
    out: List[str] = []
    if isinstance(value, (list, tuple, set)):
        for item in value:
            for piece in _as_str_list(item):
                if piece not in out:
                    out.append(piece)
    return out


def _content_type_labels(strategy_json: Optional[Dict[str, Any]]) -> List[str]:
    if not strategy_json:
        return []
    labels: List[str] = []
    for item in strategy_json.get("content_strategy_legacy") or strategy_json.get("content_strategy") or []:
        if isinstance(item, dict):
            labels.extend(_as_str_list(item.get("content_type")))
        else:
            labels.extend(_as_str_list(item))
    return labels


def _priority_factors(strategy_json: Optional[Dict[str, Any]]) -> List[str]:
    if not strategy_json:
        return []
    factors: List[str] = []
    for item in strategy_json.get("discovery_priorities") or []:
        if isinstance(item, dict) and item.get("factor"):
            factors.append(str(item["factor"]))
        elif isinstance(item, str):
            factors.append(item)
    return factors


@dataclass
class DiscoveryRequirements:
    """Single source of truth for one Discovery run."""

    campaign_id: str
    hard_platforms: List[str] = field(default_factory=list)
    hard_niches: List[str] = field(default_factory=list)
    hard_location: Optional[str] = None
    hard_subscriber_min: Optional[int] = None
    hard_subscriber_max: Optional[int] = None
    hard_creator_tiers: List[str] = field(default_factory=list)
    subscriber_ranges: List[Dict[str, Any]] = field(default_factory=list)
    excluded_categories: List[str] = field(default_factory=list)
    mandatory_keywords: List[str] = field(default_factory=list)

    preferred_creator_tiers: List[str] = field(default_factory=list)
    preferred_subscriber_min: Optional[int] = None
    preferred_subscriber_max: Optional[int] = None
    preferred_content_types: List[str] = field(default_factory=list)
    preferred_niches: List[str] = field(default_factory=list)
    creator_characteristics: List[str] = field(default_factory=list)
    priority_factors: List[str] = field(default_factory=list)

    product: str = ""
    objective: str = ""
    budget: Optional[float] = None
    target_audience: str = ""
    primary_kpi: str = ""
    description: str = ""

    def compact_campaign(self) -> Dict[str, Any]:
        sub_range = None
        if self.hard_creator_tiers:
            sub_range = {
                "source": "USER_REQUIREMENT",
                "selected_creator_tiers": self.hard_creator_tiers,
                "ranges": self.subscriber_ranges,
                "minimum": self.hard_subscriber_min,
                "maximum": self.hard_subscriber_max,
            }
        elif self.hard_subscriber_min is not None or self.hard_subscriber_max is not None:
            sub_range = {
                "minimum": self.hard_subscriber_min,
                "maximum": self.hard_subscriber_max,
                "source": "USER_REQUIREMENT",
            }
        elif self.preferred_subscriber_min is not None or self.preferred_subscriber_max is not None:
            sub_range = {
                "minimum": self.preferred_subscriber_min,
                "maximum": self.preferred_subscriber_max,
                "source": "AI_RECOMMENDATION",
            }
        return {
            "campaign_id": self.campaign_id,
            "product": self.product or "NOT_AVAILABLE",
            "objective": self.objective or "NOT_AVAILABLE",
            "budget": self.budget,
            "location": self.hard_location or "NOT_AVAILABLE",
            "platforms": self.hard_platforms,
            "niches": self.hard_niches or self.preferred_niches,
            "selected_creator_tiers": self.hard_creator_tiers,
            "subscriber_range": sub_range,
            "subscriber_ranges": self.subscriber_ranges,
            "primary_kpi": self.primary_kpi or "NOT_AVAILABLE",
            "target_audience": self.target_audience or "NOT_AVAILABLE",
        }

    def compact_strategy(self) -> Dict[str, Any]:
        return {
            "preferred_niches": self.preferred_niches,
            "preferred_creator_tiers": self.preferred_creator_tiers,
            "preferred_content_types": self.preferred_content_types,
            "creator_characteristics": self.creator_characteristics,
            "priority_factors": self.priority_factors,
            "preferred_subscriber_range": {
                "minimum": self.preferred_subscriber_min,
                "maximum": self.preferred_subscriber_max,
            },
        }

    def as_dict(self) -> Dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "hard_requirements": {
                "platform": self.hard_platforms,
                "niches": self.hard_niches,
                "location": [self.hard_location] if self.hard_location else [],
                "selected_creator_tiers": self.hard_creator_tiers,
                "subscriber_ranges": self.subscriber_ranges,
                "subscriber_min": self.hard_subscriber_min,
                "subscriber_max": self.hard_subscriber_max,
                "excluded_categories": self.excluded_categories,
                "mandatory_keywords": self.mandatory_keywords,
            },
            "strategy_preferences": self.compact_strategy(),
            "campaign_context": self.compact_campaign(),
        }

    def hard_platform_ok(self, platform: Optional[str]) -> bool:
        if not self.hard_platforms:
            return True
        return str(platform or "").lower() in {p.lower() for p in self.hard_platforms}

    def hard_subscriber_ok(self, followers: int, *, hidden: bool = False) -> bool:
        if hidden or followers <= 0:
            return True
        if self.hard_creator_tiers:
            if not followers_match_selected_tiers(
                followers, self.hard_creator_tiers, hidden=hidden
            ):
                return False
        if self.hard_subscriber_min is not None and followers < self.hard_subscriber_min:
            return False
        if self.hard_subscriber_max is not None and followers > self.hard_subscriber_max:
            return False
        return True

    def creator_tier_match_label(self, followers: int, *, hidden: bool = False) -> str:
        if hidden or followers <= 0:
            return "UNKNOWN"
        if not self.hard_creator_tiers:
            return "UNKNOWN"
        if followers_match_selected_tiers(followers, self.hard_creator_tiers, hidden=hidden):
            return "MATCH"
        return "FAIL"

    def preferred_subscriber_ok(self, followers: int, *, hidden: bool = False) -> Optional[bool]:
        if self.preferred_subscriber_min is None and self.preferred_subscriber_max is None:
            return None
        if hidden or followers <= 0:
            return None
        if self.preferred_subscriber_min is not None and followers < self.preferred_subscriber_min:
            return False
        if self.preferred_subscriber_max is not None and followers > self.preferred_subscriber_max:
            return False
        return True

    def location_match(self, country: Optional[str], location: Optional[str]) -> str:
        if not self.hard_location:
            return "UNKNOWN"
        unavailable = {
            "",
            "data_unavailable",
            "not_available",
            "unknown",
            "none",
            "n/a",
            "null",
        }

        def _usable(value: Optional[str]) -> Optional[str]:
            text = str(value or "").strip()
            if not text or text.lower() in unavailable:
                return None
            return text

        cleaned_parts = [p for p in (_usable(country), _usable(location)) if p]
        if not cleaned_parts:
            return "UNKNOWN"
        blob = " ".join(cleaned_parts).lower()
        target = self.hard_location.lower()
        if target in blob or blob in target:
            return "MATCH"
        # ISO codes vs names (IN vs India) stay UNKNOWN rather than FALSE.
        if all(len(p) <= 3 for p in cleaned_parts):
            return "UNKNOWN"
        return "FAIL"

    def subscriber_match_label(self, followers: int, *, hidden: bool = False) -> str:
        if hidden or followers <= 0:
            return "UNKNOWN"
        if not self.hard_subscriber_ok(followers, hidden=hidden):
            return "FAIL"
        pref = self.preferred_subscriber_ok(followers, hidden=hidden)
        if pref is False:
            return "PARTIAL"
        return "MATCH"


def build_discovery_requirements(
    campaign: Campaign,
    strategy_json: Optional[Dict[str, Any]] = None,
) -> DiscoveryRequirements:
    strategy_json = strategy_json or {}
    creator = strategy_json.get("creator_strategy") or {}
    strat_niches = _as_str_list(creator.get("preferred_niches")) or _as_str_list(
        strategy_json.get("preferred_niches")
    )
    user_niches = _as_str_list(getattr(campaign, "interests", None)) or _as_str_list(
        getattr(campaign, "keywords", None)
    )
    location = None
    target_locations = getattr(campaign, "target_locations", None)
    if target_locations:
        parts = [p.strip() for p in str(target_locations).split(",") if p.strip()]
        location = parts[0] if parts else None
    if not location:
        locs = _as_str_list(creator.get("preferred_locations"))
        location = locs[0] if locs else None

    strat_min, strat_max = extract_subscriber_range(strategy_json)
    user_min = getattr(campaign, "min_followers", None)
    user_max = getattr(campaign, "max_followers", None)
    user_tiers = selected_tier_keys(getattr(campaign, "creator_tiers", None) or [])
    apply_campaign_minmax = True
    if user_tiers:
        apply_campaign_minmax = campaign_min_max_compatible_with_tiers(
            user_tiers, user_min, user_max
        )

    characteristics = _as_str_list(creator.get("desired_creator_characteristics"))
    characteristics.extend(_as_str_list(creator.get("creator_characteristics")))

    return DiscoveryRequirements(
        campaign_id=getattr(campaign, "id", "") or "",
        hard_platforms=[str(p) for p in (getattr(campaign, "platforms", None) or []) if p],
        hard_niches=user_niches,
        hard_location=location,
        hard_subscriber_min=int(user_min) if apply_campaign_minmax and user_min is not None else None,
        hard_subscriber_max=int(user_max) if apply_campaign_minmax and user_max is not None else None,
        hard_creator_tiers=user_tiers,
        subscriber_ranges=subscriber_ranges_for_tiers(user_tiers),
        mandatory_keywords=_as_str_list(getattr(campaign, "keywords", None)),
        preferred_creator_tiers=user_tiers
        or sorted(preferred_tier_keys(strategy_json))
        or _as_str_list(getattr(campaign, "creator_tiers", None)),
        preferred_subscriber_min=strat_min if not user_tiers and user_min is None else None,
        preferred_subscriber_max=strat_max if not user_tiers and user_max is None else None,
        preferred_content_types=_content_type_labels(strategy_json)
        or _as_str_list(getattr(campaign, "campaign_types", None)),
        preferred_niches=strat_niches or user_niches,
        creator_characteristics=characteristics,
        priority_factors=_priority_factors(strategy_json),
        product=getattr(campaign, "name", "") or "",
        objective=getattr(campaign, "objective", "") or "",
        budget=float(campaign.budget) if getattr(campaign, "budget", None) else None,
        target_audience=target_locations or "",
        primary_kpi=getattr(campaign, "primary_kpi", "") or "",
        description=getattr(campaign, "description", "") or "",
    )


def deterministic_requirement_score(
    *,
    followers: int,
    platform: str,
    description: str,
    niches: List[str],
    recent_titles: List[str],
    existing_score: Optional[float],
    reqs: DiscoveryRequirements,
    hidden: bool = False,
) -> float:
    """0–100 score from real data + requirement satisfaction. Never uses Groq."""
    base = float(existing_score or 0)
    haystack = " ".join(
        [
            description or "",
            " ".join(niches or []),
            " ".join(recent_titles or []),
        ]
    ).lower()
    search_terms = [t.lower() for t in (reqs.hard_niches or reqs.preferred_niches) if t]
    hits = sum(1 for t in search_terms if t.lower() in haystack) if search_terms else 0
    niche_bonus = 0.0
    if search_terms:
        niche_bonus = min(25.0, (hits / max(1, min(len(search_terms), 3))) * 25.0)

    range_bonus = 0.0
    if reqs.hard_subscriber_ok(followers, hidden=hidden):
        range_bonus += 10.0
        pref = reqs.preferred_subscriber_ok(followers, hidden=hidden)
        if pref is True:
            range_bonus += 10.0
        elif pref is False:
            range_bonus -= 8.0
    else:
        range_bonus -= 40.0

    platform_bonus = 10.0 if reqs.hard_platform_ok(platform) else -40.0
    loc = reqs.location_match(None, None)
    # Location is scored only when real country is passed via description/country later.
    score = base * 0.5 + niche_bonus + range_bonus + platform_bonus
    return max(0.0, min(100.0, round(score, 2)))


def eligibility_for_creator(
    *,
    platform: str,
    followers: int,
    hidden: bool,
    reqs: DiscoveryRequirements,
) -> Tuple[str, Dict[str, str]]:
    platform_label = "MATCH" if reqs.hard_platform_ok(platform) else "FAIL"
    sub_label = reqs.subscriber_match_label(followers, hidden=hidden)
    tier_label = reqs.creator_tier_match_label(followers, hidden=hidden)
    eligible = platform_label != "FAIL" and sub_label != "FAIL" and tier_label != "FAIL"
    return ("ELIGIBLE" if eligible else "NOT_ELIGIBLE", {
        "platform": platform_label,
        "subscriber_range": sub_label if sub_label != "PARTIAL" else "MATCH",
        "creator_tier": tier_label,
    })
