"""Deterministic, explainable campaign/creator match scoring.

No randomness and no invented data: every factor is derived from values that were
actually returned by the platform API. When a signal is unavailable the factor is
skipped and its weight is redistributed across the remaining factors, so a creator
is never penalised for data YouTube simply does not publish.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.campaign import Campaign

# Factor weights (sum to 100 when every signal is available).
# Niche/content evidence outranks raw popularity.
WEIGHT_KEYWORD_RELEVANCE = 40
WEIGHT_FOLLOWER_SUITABILITY = 15
WEIGHT_ENGAGEMENT = 20
WEIGHT_RECENT_ACTIVITY = 15
WEIGHT_LOCATION = 10

# Engagement rate (%) treated as a full-credit result for subscriber-based YouTube maths.
ENGAGEMENT_TARGET_PERCENT = 5.0

_STOPWORDS = {
    "the", "and", "for", "with", "your", "our", "from", "into", "this", "that",
    "campaign", "launch", "brand", "new", "best", "top", "india", "indian",
}

# Only well-known, unambiguous mappings. Anything else stays unresolved rather than guessed.
_COUNTRY_CODES: Dict[str, str] = {
    "india": "IN",
    "united states": "US",
    "usa": "US",
    "united kingdom": "GB",
    "uk": "GB",
    "canada": "CA",
    "australia": "AU",
    "germany": "DE",
    "france": "FR",
    "singapore": "SG",
    "united arab emirates": "AE",
    "uae": "AE",
}

# Cities/regions mapped to their country so "Mumbai, Delhi" still resolves to IN.
_CITY_TO_COUNTRY: Dict[str, str] = {
    "mumbai": "IN", "delhi": "IN", "new delhi": "IN", "bangalore": "IN",
    "bengaluru": "IN", "hyderabad": "IN", "chennai": "IN", "kolkata": "IN",
    "pune": "IN", "ahmedabad": "IN", "goa": "IN", "kochi": "IN", "jaipur": "IN",
    "london": "GB", "manchester": "GB",
    "new york": "US", "los angeles": "US", "san francisco": "US", "chicago": "US",
    "toronto": "CA", "vancouver": "CA",
    "sydney": "AU", "melbourne": "AU",
    "dubai": "AE", "abu dhabi": "AE",
}


@dataclass
class MatchFactor:
    key: str
    label: str
    weight: int
    score: Optional[float]  # 0.0 - 1.0, or None when the signal is unavailable
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "weight": self.weight,
            "score": None if self.score is None else round(self.score, 4),
            "available": self.score is not None,
            "detail": self.detail,
        }


@dataclass
class MatchResult:
    score: Optional[int]
    factors: List[MatchFactor] = field(default_factory=list)

    @property
    def reasons(self) -> List[str]:
        return [f.detail for f in self.factors]

    def to_payload(self) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self.factors]


@dataclass
class CreatorSignals:
    """Real, platform-sourced values used for scoring. None means 'not provided'."""

    name: str = ""
    description: Optional[str] = None
    followers: Optional[int] = None
    engagement_rate: Optional[float] = None
    metrics_sample_size: int = 0
    last_upload_at: Optional[datetime] = None
    country: Optional[str] = None
    extra_text: Optional[str] = None


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) > 2]


def resolve_target_country(campaign: Campaign) -> Optional[str]:
    """Resolve an ISO-3166 alpha-2 code from the campaign's target locations.

    Returns None when the text cannot be mapped confidently.
    """
    raw = (campaign.target_locations or "").strip()
    if not raw:
        return None

    for part in [p.strip().lower() for p in raw.split(",") if p.strip()]:
        if len(part) == 2 and part.isalpha():
            return part.upper()
        if part in _COUNTRY_CODES:
            return _COUNTRY_CODES[part]
        if part in _CITY_TO_COUNTRY:
            return _CITY_TO_COUNTRY[part]
    return None


def build_campaign_terms(campaign: Campaign) -> List[str]:
    """Collect the campaign's own vocabulary used for keyword relevance."""
    terms: List[str] = []
    for source in (campaign.keywords, campaign.interests, campaign.campaign_types):
        for value in source or []:
            terms.extend(_tokenize(str(value)))

    for value in (campaign.objective, campaign.name):
        if value:
            terms.extend(_tokenize(str(value)))

    deduped: List[str] = []
    for t in terms:
        if t not in deduped and t not in _STOPWORDS:
            deduped.append(t)
    return deduped


class CreatorScoringService:
    """Scores one creator against one campaign brief."""

    @staticmethod
    def _score_keyword_relevance(campaign_terms: List[str], signals: CreatorSignals) -> MatchFactor:
        if not campaign_terms:
            return MatchFactor(
                key="keyword_relevance",
                label="Niche & keyword relevance",
                weight=WEIGHT_KEYWORD_RELEVANCE,
                score=None,
                detail="Campaign has no keywords or interests to match against.",
            )

        haystack = f"{signals.name} {signals.description or ''} {signals.extra_text or ''}".lower()
        matched = [t for t in campaign_terms if t in haystack]

        # Three solid keyword hits is treated as a strong topical signal.
        denominator = max(1, min(len(campaign_terms), 3))
        score = min(1.0, len(matched) / denominator)

        if matched:
            detail = f"Matched campaign keywords in channel content: {', '.join(matched[:5])}."
        else:
            detail = "No campaign keywords found in the channel title or description."

        return MatchFactor(
            key="keyword_relevance",
            label="Niche & keyword relevance",
            weight=WEIGHT_KEYWORD_RELEVANCE,
            score=score,
            detail=detail,
        )

    @staticmethod
    def _score_follower_suitability(campaign: Campaign, signals: CreatorSignals) -> MatchFactor:
        weight = WEIGHT_FOLLOWER_SUITABILITY
        followers = signals.followers

        if not followers or followers <= 0:
            return MatchFactor(
                key="follower_suitability",
                label="Subscriber suitability",
                weight=weight,
                score=None,
                detail="Subscriber count is hidden by the creator, so size fit cannot be assessed.",
            )

        min_f = campaign.min_followers
        max_f = campaign.max_followers

        if not min_f and not max_f:
            return MatchFactor(
                key="follower_suitability",
                label="Subscriber suitability",
                weight=weight,
                score=1.0,
                detail=f"{followers:,} subscribers. Campaign specifies no subscriber range.",
            )

        if min_f and followers < min_f:
            score = max(0.0, followers / min_f)
            detail = f"{followers:,} subscribers is below the campaign minimum of {min_f:,}."
        elif max_f and followers > max_f:
            score = max(0.0, max_f / followers)
            detail = f"{followers:,} subscribers exceeds the campaign maximum of {max_f:,}."
        else:
            score = 1.0
            bounds = f"{min_f:,}" if min_f else "0"
            upper = f"{max_f:,}" if max_f else "no upper limit"
            detail = f"{followers:,} subscribers fits the campaign target range ({bounds}–{upper})."

        return MatchFactor(
            key="follower_suitability",
            label="Subscriber suitability",
            weight=weight,
            score=score,
            detail=detail,
        )

    @staticmethod
    def _score_engagement(signals: CreatorSignals) -> MatchFactor:
        weight = WEIGHT_ENGAGEMENT

        if signals.engagement_rate is None or signals.metrics_sample_size <= 0:
            return MatchFactor(
                key="engagement",
                label="Audience engagement",
                weight=weight,
                score=None,
                detail="Not enough recent video statistics to derive an engagement rate.",
            )

        score = min(1.0, max(0.0, signals.engagement_rate / ENGAGEMENT_TARGET_PERCENT))
        return MatchFactor(
            key="engagement",
            label="Audience engagement",
            weight=weight,
            score=score,
            detail=(
                f"{signals.engagement_rate:.2f}% engagement derived from the "
                f"{signals.metrics_sample_size} most recent videos."
            ),
        )

    @staticmethod
    def _score_recent_activity(signals: CreatorSignals) -> MatchFactor:
        weight = WEIGHT_RECENT_ACTIVITY

        if not signals.last_upload_at:
            return MatchFactor(
                key="recent_activity",
                label="Publishing activity",
                weight=weight,
                score=None,
                detail="Latest upload date is unavailable for this channel.",
            )

        last = signals.last_upload_at
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = max(0, (datetime.now(timezone.utc) - last).days)

        if days <= 30:
            score = 1.0
        elif days <= 60:
            score = 0.8
        elif days <= 90:
            score = 0.6
        elif days <= 180:
            score = 0.35
        else:
            score = 0.1

        return MatchFactor(
            key="recent_activity",
            label="Publishing activity",
            weight=weight,
            score=score,
            detail=f"Most recent upload was {days} day(s) ago.",
        )

    @staticmethod
    def _score_location(target_country: Optional[str], signals: CreatorSignals) -> MatchFactor:
        weight = WEIGHT_LOCATION

        if not target_country:
            return MatchFactor(
                key="location",
                label="Location relevance",
                weight=weight,
                score=None,
                detail="Campaign target location could not be resolved to a country.",
            )
        if not signals.country:
            return MatchFactor(
                key="location",
                label="Location relevance",
                weight=weight,
                score=None,
                detail="Location unavailable — YouTube does not publish a country for this channel.",
            )

        match = signals.country.upper() == target_country.upper()
        return MatchFactor(
            key="location",
            label="Location relevance",
            weight=weight,
            score=1.0 if match else 0.0,
            detail=(
                f"Channel country {signals.country.upper()} matches campaign target {target_country}."
                if match
                else f"Channel country {signals.country.upper()} differs from campaign target {target_country}."
            ),
        )

    @classmethod
    def score(
        cls,
        campaign: Campaign,
        signals: CreatorSignals,
        campaign_terms: Optional[List[str]] = None,
        target_country: Optional[str] = None,
    ) -> MatchResult:
        terms = campaign_terms if campaign_terms is not None else build_campaign_terms(campaign)
        country = target_country if target_country is not None else resolve_target_country(campaign)

        factors = [
            cls._score_keyword_relevance(terms, signals),
            cls._score_follower_suitability(campaign, signals),
            cls._score_engagement(signals),
            cls._score_recent_activity(signals),
            cls._score_location(country, signals),
        ]

        available = [f for f in factors if f.score is not None]
        if not available:
            return MatchResult(score=None, factors=factors)

        total_weight = sum(f.weight for f in available)
        weighted = sum(f.weight * (f.score or 0.0) for f in available)
        score = int(round((weighted / total_weight) * 100))

        return MatchResult(score=max(0, min(100, score)), factors=factors)
