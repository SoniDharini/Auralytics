"""Normalized Discovery requirements: hard user constraints vs Strategy preferences.

User requirements always outrank Strategy Agent recommendations.
This module does not invent campaign facts and does not call Groq.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from app.ai.audience_profile import AudienceProfile, PERSONA_UNKNOWN, build_audience_profile
from app.ai.creator_entity import is_collaborable_entity
from app.ai.creator_tiers import (
    campaign_min_max_compatible_with_tiers,
    extract_subscriber_range,
    followers_match_selected_tiers,
    preferred_tier_keys,
    selected_tier_keys,
    subscriber_ranges_for_tiers,
)
from app.models.campaign import Campaign
from app.services.creator_scoring_service import _CITY_TO_COUNTRY, _COUNTRY_CODES

_EXCLUSIVE_NICHE_RE = re.compile(
    r"\bonly\s+([a-z0-9][\w\s-]{1,40}?)\s+(?:influencers?|creators?|youtubers?)\b",
    re.IGNORECASE,
)
_VIEW_REQ_RE = re.compile(
    r"(?:minimum|min(?:imum)?)\s+(?:recent\s+)?(?:avg(?:erage)?\s+)?views?\s*[:=]?\s*([\d,.]+)\s*(k|m|million|thousand)?",
    re.IGNORECASE,
)


def parse_exclusive_niches(*parts: Any) -> List[str]:
    """User-exclusive niche, e.g. 'Only fitness influencers'. Empty unless explicitly required."""
    text = " ".join(str(p or "") for p in parts)
    found: List[str] = []
    for match in _EXCLUSIVE_NICHE_RE.finditer(text):
        term = re.sub(r"\s+", " ", match.group(1).strip().lower())
        if term and term not in found:
            found.append(term)
    return found


def parse_view_count(raw: Any) -> Optional[int]:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        value = int(raw)
        return value if value > 0 else None
    text = str(raw).strip().lower().replace(",", "")
    match = re.fullmatch(r"([\d.]+)\s*(k|m|million|thousand)?", text)
    if not match:
        return None
    try:
        number = float(match.group(1))
    except (TypeError, ValueError):
        return None
    suffix = match.group(2) or ""
    if suffix in ("k", "thousand"):
        number *= 1000
    elif suffix in ("m", "million"):
        number *= 1_000_000
    return int(number) if number > 0 else None


def extract_view_requirement(*parts: Any) -> Optional[int]:
    blob = " ".join(str(p or "") for p in parts)
    match = _VIEW_REQ_RE.search(blob)
    if not match:
        return None
    suffix = match.group(2) or ""
    return parse_view_count(f"{match.group(1)}{suffix}")


def extract_strategy_view_preference(strategy_json: Optional[Dict[str, Any]]) -> Optional[int]:
    if not strategy_json:
        return None
    creator = strategy_json.get("creator_strategy") or {}
    discovery = strategy_json.get("discovery_requirements") or {}
    for raw in (
        discovery.get("minimum_recent_views"),
        discovery.get("preferred_min_avg_views"),
        creator.get("preferred_min_avg_views"),
        creator.get("recommended_min_views"),
        strategy_json.get("preferred_min_avg_views"),
    ):
        parsed = parse_view_count(raw)
        if parsed:
            return parsed
    return None


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
    explicit_niche_required: bool = False
    product_terms: List[str] = field(default_factory=list)
    hard_recent_views_min: Optional[int] = None
    preferred_recent_views_min: Optional[int] = None

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
    target_age_min: Optional[int] = None
    target_age_max: Optional[int] = None
    audience: Optional[AudienceProfile] = None

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
        audience = self.audience
        persona_block = {
            "target_persona": (audience.persona if audience else PERSONA_UNKNOWN),
            "age_range": {
                "minimum": self.target_age_min,
                "maximum": self.target_age_max,
            },
            "location": self.hard_location or "NOT_AVAILABLE",
            "campaign_objective": self.objective or "NOT_AVAILABLE",
            "creator_tiers": self.hard_creator_tiers,
            "subscriber_min": self.hard_subscriber_min,
            "subscriber_max": self.hard_subscriber_max,
            "minimum_recent_views": self.hard_recent_views_min,
            "preferred_recent_views": self.preferred_recent_views_min,
            "explicit_niche": self.hard_niches if self.explicit_niche_required else [],
            "single_creator_required": True,
        }
        return {
            "campaign_id": self.campaign_id,
            "product": self.product or "NOT_AVAILABLE",
            "product_name": self.product or "NOT_AVAILABLE",
            "product_description": self.description or "NOT_AVAILABLE",
            "campaign_description": self.description or "NOT_AVAILABLE",
            "campaign_objective": self.objective or "NOT_AVAILABLE",
            "objective": self.objective or "NOT_AVAILABLE",
            "budget": self.budget,
            "location": self.hard_location or "NOT_AVAILABLE",
            "platforms": self.hard_platforms,
            "niches": self.hard_niches or self.product_terms or self.preferred_niches,
            "selected_creator_tiers": self.hard_creator_tiers,
            "subscriber_range": sub_range,
            "subscriber_ranges": self.subscriber_ranges,
            "primary_kpi": self.primary_kpi or "NOT_AVAILABLE",
            "target_audience": self.target_audience or "NOT_AVAILABLE",
            "description": self.description or "NOT_AVAILABLE",
            "target_age_min": self.target_age_min,
            "target_age_max": self.target_age_max,
            "target_persona": (audience.persona if audience else PERSONA_UNKNOWN),
            "persona_source": (audience.source if audience else "UNKNOWN"),
            "persona_terms": list(audience.terms) if audience else [],
            "customer_persona": persona_block,
            "minimum_recent_views": self.hard_recent_views_min,
            "preferred_recent_views": self.preferred_recent_views_min,
            "explicit_niche_required": self.explicit_niche_required,
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
            "preferred_min_avg_views": self.preferred_recent_views_min,
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
                "explicit_niche_required": self.explicit_niche_required,
                "minimum_recent_views": self.hard_recent_views_min,
            },
            "strategy_preferences": self.compact_strategy(),
            "campaign_context": self.compact_campaign(),
        }

    def hard_platform_ok(self, platform: Optional[str]) -> bool:
        if not self.hard_platforms:
            return True
        return str(platform or "").lower() in {p.lower() for p in self.hard_platforms}

    def requires_subscriber_facts(self) -> bool:
        return bool(
            self.hard_creator_tiers
            or self.hard_subscriber_min is not None
            or self.hard_subscriber_max is not None
        )

    def hard_subscriber_ok(self, followers: int, *, hidden: bool = False) -> bool:
        if hidden or followers <= 0:
            return not self.requires_subscriber_facts()
        if self.hard_creator_tiers:
            if not followers_match_selected_tiers(
                followers, self.hard_creator_tiers, hidden=False
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
        if followers_match_selected_tiers(followers, self.hard_creator_tiers, hidden=False):
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

    @staticmethod
    def _iso_code(value: Optional[str]) -> Optional[str]:
        text = str(value or "").strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered in {
            "data_unavailable",
            "not_available",
            "unknown",
            "none",
            "n/a",
            "null",
        }:
            return None
        if len(text) == 2 and text.isalpha():
            return text.upper()
        if lowered in _COUNTRY_CODES:
            return _COUNTRY_CODES[lowered]
        if lowered in _CITY_TO_COUNTRY:
            return _CITY_TO_COUNTRY[lowered]
        return None

    def location_match(self, country: Optional[str], location: Optional[str]) -> str:
        if not self.hard_location:
            return "UNKNOWN"
        target = self._iso_code(self.hard_location) or str(self.hard_location).strip().upper()
        creator = self._iso_code(country) or self._iso_code(location)
        if not creator:
            parts = [str(country or "").strip(), str(location or "").strip()]
            unknown_tokens = {
                "",
                "data_unavailable",
                "not_available",
                "unknown",
                "none",
                "n/a",
                "null",
            }
            meaningful = [p for p in parts if p.lower() not in unknown_tokens]
            if not meaningful:
                return "UNKNOWN"
            blob = " ".join(meaningful).lower()
            needle = str(self.hard_location).lower()
            if needle in blob or blob in needle:
                return "MATCH"
            return "FAIL"
        if len(target) == 2 and creator == target:
            return "MATCH"
        if creator == target:
            return "MATCH"
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

    def view_match_label(self, recent_avg_views: Optional[int]) -> str:
        views = 0
        try:
            views = int(recent_avg_views or 0)
        except (TypeError, ValueError):
            views = 0
        if self.hard_recent_views_min is None and self.preferred_recent_views_min is None:
            return "UNKNOWN"
        if views <= 0:
            return "UNKNOWN"
        if self.hard_recent_views_min is not None and views < self.hard_recent_views_min:
            return "FAIL"
        if (
            self.preferred_recent_views_min is not None
            and views < self.preferred_recent_views_min
            and self.hard_recent_views_min is None
        ):
            return "PARTIAL"
        return "MATCH"

    def completeness_status(
        self,
        *,
        name: Optional[str] = None,
        followers: int = 0,
        hidden: bool = False,
        recent_avg_views: Optional[int] = None,
        metrics_sample_size: int = 0,
        country: Optional[str] = None,
        location: Optional[str] = None,
    ) -> str:
        """OK or INSUFFICIENT_DATA. Missing facts are never treated as matches."""
        if name is not None and not str(name).strip():
            return "INSUFFICIENT_DATA"
        if self.requires_subscriber_facts() and (hidden or int(followers or 0) <= 0):
            return "INSUFFICIENT_DATA"
        if self.hard_location:
            loc = self.location_match(country, location)
            if loc == "UNKNOWN" and (country is not None or location is not None):
                return "INSUFFICIENT_DATA"
        if self.hard_recent_views_min is not None and int(metrics_sample_size or 0) <= 0:
            return "INSUFFICIENT_DATA"
        views = 0
        try:
            views = int(recent_avg_views or 0)
        except (TypeError, ValueError):
            views = 0
        if self.hard_recent_views_min is not None and views <= 0:
            return "INSUFFICIENT_DATA"
        return "OK"

    def hard_views_ok(self, recent_avg_views: Optional[int]) -> bool:
        return self.view_match_label(recent_avg_views) != "FAIL"


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

    description = getattr(campaign, "description", "") or ""
    age_min = getattr(campaign, "target_age_min", None)
    age_max = getattr(campaign, "target_age_max", None)
    audience = build_audience_profile(
        description=description,
        interests=getattr(campaign, "interests", None),
        objective=getattr(campaign, "objective", None),
        target_age_min=age_min,
        target_age_max=age_max,
        extra_text=" ".join(characteristics),
    )
    audience_bits = []
    if audience.persona and audience.persona != PERSONA_UNKNOWN:
        audience_bits.append(audience.persona)
    if age_min is not None or age_max is not None:
        audience_bits.append(f"{age_min or '?'}-{age_max or '?'}")
    if getattr(campaign, "target_gender", None):
        audience_bits.append(str(campaign.target_gender))

    exclusive = parse_exclusive_niches(
        description,
        " ".join(_as_str_list(getattr(campaign, "keywords", None))),
        " ".join(_as_str_list(getattr(campaign, "interests", None))),
        " ".join(characteristics),
    )
    user_view_min = extract_view_requirement(
        description,
        " ".join(_as_str_list(getattr(campaign, "keywords", None))),
    )
    strategy_view_min = extract_strategy_view_preference(strategy_json)

    return DiscoveryRequirements(
        campaign_id=getattr(campaign, "id", "") or "",
        hard_platforms=[str(p) for p in (getattr(campaign, "platforms", None) or []) if p],
        hard_niches=exclusive,
        hard_location=location,
        hard_subscriber_min=int(user_min) if apply_campaign_minmax and user_min is not None else None,
        hard_subscriber_max=int(user_max) if apply_campaign_minmax and user_max is not None else None,
        hard_creator_tiers=user_tiers,
        subscriber_ranges=subscriber_ranges_for_tiers(user_tiers),
        mandatory_keywords=_as_str_list(getattr(campaign, "keywords", None)),
        explicit_niche_required=bool(exclusive),
        product_terms=user_niches,
        hard_recent_views_min=user_view_min,
        preferred_recent_views_min=None if user_view_min is not None else strategy_view_min,
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
        target_audience=", ".join(audience_bits) if audience_bits else (description[:180] or ""),
        primary_kpi=getattr(campaign, "primary_kpi", "") or "",
        description=description,
        target_age_min=int(age_min) if age_min is not None else None,
        target_age_max=int(age_max) if age_max is not None else None,
        audience=audience,
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
    country: Optional[str] = None,
    location: Optional[str] = None,
    entity_type: Optional[str] = None,
    recent_avg_views: Optional[int] = None,
    metrics_sample_size: int = 0,
    name: Optional[str] = None,
) -> Tuple[str, Dict[str, str]]:
    completeness = reqs.completeness_status(
        name=name,
        followers=followers,
        hidden=hidden,
        recent_avg_views=recent_avg_views,
        metrics_sample_size=metrics_sample_size,
        country=country,
        location=location,
    )
    platform_label = "MATCH" if reqs.hard_platform_ok(platform) else "FAIL"
    sub_label = reqs.subscriber_match_label(followers, hidden=hidden)
    tier_label = reqs.creator_tier_match_label(followers, hidden=hidden)
    loc_label = reqs.location_match(country, location)
    view_label = reqs.view_match_label(recent_avg_views)
    entity = str(entity_type or "").upper()
    entity_label = "UNKNOWN"
    if entity:
        entity_label = "MATCH" if is_collaborable_entity(entity) else "FAIL"
    if completeness != "OK":
        return ("INSUFFICIENT_DATA", {
            "platform": platform_label,
            "subscriber_range": sub_label,
            "creator_tier": tier_label,
            "location": loc_label,
            "creator_entity": entity_label,
            "view_requirement": view_label,
        })
    eligible = (
        platform_label != "FAIL"
        and sub_label != "FAIL"
        and tier_label != "FAIL"
        and loc_label != "FAIL"
        and entity_label != "FAIL"
        and view_label != "FAIL"
    )
    return ("ELIGIBLE" if eligible else "NOT_ELIGIBLE", {
        "platform": platform_label,
        "subscriber_range": sub_label if sub_label != "PARTIAL" else "MATCH",
        "creator_tier": tier_label,
        "location": loc_label,
        "creator_entity": entity_label,
        "view_requirement": view_label,
    })
