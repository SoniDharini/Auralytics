from typing import Any, Dict, Iterable, List, Optional
import re
from app.ai.audience_profile import (
    PERSONA_ADULT,
    PERSONA_GEN_Z,
    PERSONA_MATURE,
    PERSONA_UNKNOWN,
    build_audience_profile,
)
from app.ai.discovery_requirements import parse_exclusive_niches
from app.models.campaign import Campaign

# Words that add no discovery signal on their own.
_NOISE_WORDS = {
    "the", "and", "for", "with", "your", "our", "from", "into", "this", "that",
    "campaign", "launch", "new", "best", "top", "phase", "season",
}

# Strategy priority labels that are scoring hints, not YouTube search terms.
_GENERIC_PRIORITY_WORDS = {
    "niche match",
    "audience alignment",
    "audience match",
    "engagement",
    "engagement quality",
    "content relevance",
    "brand fit",
    "campaign fit",
}


class CampaignQueryBuilder:
    """Builds targeted search queries from the campaign brief plus saved Strategy Agent output.

    Queries are derived from campaign fields and persisted strategy niches. Nothing is
    hardcoded, and the set is deliberately small because each YouTube search costs 100 quota units.
    """

    @staticmethod
    def clean_keyword(text: str) -> str:
        return re.sub(r"[^\w\s-]", "", str(text)).strip()

    @classmethod
    def resolve_location(cls, campaign: Campaign, strategy: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if campaign.target_locations:
            parts = [cls.clean_keyword(p) for p in campaign.target_locations.split(",") if p.strip()]
            if parts:
                return parts[0]
        for loc in cls._strategy_locations(strategy or {}):
            cleaned = cls.clean_keyword(loc)
            if cleaned:
                return cleaned
        return None

    @classmethod
    def _content_intent_words(cls, strategy: Optional[Dict[str, Any]], campaign: Campaign) -> List[str]:
        """Map campaign/strategy content preferences into YouTube search intents."""
        raw: List[str] = []
        cls._collect_terms(raw, campaign.campaign_types)
        for item in (strategy or {}).get("content_strategy_legacy") or (strategy or {}).get("content_strategy") or []:
            if isinstance(item, dict):
                cls._collect_terms(raw, item.get("content_type"))
            else:
                cls._collect_terms(raw, item)
        blob = " ".join(raw).lower()
        blob = f"{blob} {str(campaign.objective or '').lower()} {str(campaign.name or '').lower()}"
        intents: List[str] = []
        if any(w in blob for w in ("review", "unbox", "demo", "launch", "comparison", "versus")):
            intents.append("review")
        if any(w in blob for w in ("tutorial", "how to", "routine", "guide", "educational")):
            intents.append("tutorial")
        if any(w in blob for w in ("vlog", "haul", "routine")):
            intents.append("routine")
        return intents

    @classmethod
    def build_queries(
        cls,
        campaign: Campaign,
        max_queries: int = 5,
        strategy: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        location = cls.resolve_location(campaign, strategy)
        intents = cls._content_intent_words(strategy, campaign)
        profile = build_audience_profile(
            description=getattr(campaign, "description", None),
            interests=getattr(campaign, "interests", None),
            objective=getattr(campaign, "objective", None),
            target_age_min=getattr(campaign, "target_age_min", None),
            target_age_max=getattr(campaign, "target_age_max", None),
        )
        persona_concepts = cls._persona_search_concepts(profile.persona, campaign)
        exclusive = parse_exclusive_niches(
            getattr(campaign, "description", None),
            " ".join(campaign.keywords or []),
            " ".join(campaign.interests or []),
        )
        persona_first = bool(persona_concepts) and not exclusive and profile.persona != PERSONA_UNKNOWN
        if exclusive:
            persona_slots = 0
            product_limit = max_queries
        elif persona_first:
            persona_slots = min(len(persona_concepts), max(2, max_queries - 1))
            product_limit = max(1, max_queries - persona_slots)
        else:
            persona_slots = min(2, len(persona_concepts)) if persona_concepts else 0
            product_limit = max(1, max_queries - persona_slots)

        def compose(term: str, extra: str = "") -> str:
            term = cls.clean_keyword(term)
            extra = cls.clean_keyword(extra) if extra else ""
            if not term:
                return ""
            parts = [p for p in (term, extra, location) if p]
            return " ".join(parts).strip()

        queries: List[str] = []

        def push(value: str, *, cap: Optional[int] = None) -> None:
            limit = cap if cap is not None else max_queries
            if value and value not in queries and len(queries) < limit:
                queries.append(value)

        if persona_first:
            for concept in persona_concepts:
                push(compose(concept), cap=persona_slots)

        product_cap = max_queries if (persona_first or exclusive) else product_limit

        for keyword in campaign.keywords or []:
            push(compose(keyword), cap=product_cap)
            if len(queries) < product_cap:
                for intent in intents[:2]:
                    push(compose(keyword, intent), cap=product_cap)
            if len(queries) < product_cap and "review" in intents:
                push(compose(keyword, "reviewer"), cap=product_cap)

        for interest in campaign.interests or []:
            push(compose(interest), cap=product_cap)
            if len(queries) < product_cap:
                for intent in intents[:1]:
                    push(compose(interest, intent), cap=product_cap)

        for niche in cls._strategy_search_terms(strategy or {}):
            push(compose(niche), cap=product_cap)
            if len(queries) < product_cap:
                for intent in intents[:1]:
                    push(compose(niche, intent), cap=product_cap)

        for campaign_type in campaign.campaign_types or []:
            push(compose(campaign_type), cap=product_cap)

        if not persona_first:
            for concept in persona_concepts:
                push(compose(concept))

        # 6. Thematic words from the campaign name, only if we still need queries.
        if len(queries) < max_queries and campaign.name:
            words = [
                cls.clean_keyword(w)
                for w in campaign.name.split()
                if len(w) > 3 and w.lower() not in _NOISE_WORDS
            ]
            words = [w for w in words if w]
            if words:
                push(compose(" ".join(words[:2])))

        # 6. Last resort: brand or objective context.
        if not queries and campaign.brand:
            push(compose(campaign.brand))
        if not queries and campaign.objective:
            push(compose(campaign.objective))

        # An empty list is a valid outcome; the caller surfaces a "brief too thin"
        # error rather than inventing a niche to search for.
        return queries[:max_queries]

    @classmethod
    def _persona_search_concepts(cls, persona: str, campaign: Campaign) -> List[str]:
        """Audience-first search concepts. Product keywords stay in earlier query slots."""
        desc = " ".join(
            [
                str(campaign.description or ""),
                str(campaign.objective or ""),
                " ".join(campaign.interests or []),
                " ".join(campaign.keywords or []),
            ]
        ).lower()
        tiers = [str(t).lower() for t in (campaign.creator_tiers or [])]
        celebrity = any("celeb" in t or "mega" in t for t in tiers)

        def with_fallbacks(primary: List[str], extras: List[str]) -> List[str]:
            out = list(primary)
            for item in extras:
                if item not in out:
                    out.append(item)
            return out

        if persona == PERSONA_GEN_Z:
            concepts = ["trending individual creators", "popular youth creators"]
            if celebrity:
                concepts.insert(1, "popular individual creators")
            if any(w in desc for w in ("college", "campus", "party")):
                concepts.append("college youth creators")
            if any(w in desc for w in ("comedy", "funny", "roast")):
                concepts.append("comedy creators")
            if any(w in desc for w in ("game", "gaming", "esport")):
                concepts.append("gaming creators")
            if any(w in desc for w in ("fashion", "style", "beauty")):
                concepts.append("fashion creators")
            if any(w in desc for w in ("tech", "gadget", "phone")):
                concepts.append("technology creators")
            if any(w in desc for w in ("music", "pop culture")):
                concepts.append("pop culture creators")
            return with_fallbacks(
                concepts,
                [
                    "entertainment creators",
                    "comedy creators",
                    "lifestyle YouTubers",
                    "gaming creators",
                    "pop culture creators",
                ],
            )
        if persona == PERSONA_ADULT:
            concepts = ["working professional creators", "adult lifestyle creators"]
            if any(w in desc for w in ("finance", "money", "invest", "business")):
                concepts.insert(0, "finance business creators")
            if any(w in desc for w in ("auto", "car", "vehicle")):
                concepts.append("automobile creators")
            if any(w in desc for w in ("travel", "trip")):
                concepts.append("travel creators")
            if any(w in desc for w in ("career", "job", "work")):
                concepts.append("career creators")
            if any(w in desc for w in ("health", "fitness", "wellness")):
                concepts.append("health lifestyle creators")
            return with_fallbacks(concepts, ["career creators", "practical lifestyle creators"])
        if persona == PERSONA_MATURE:
            return [
                "mature lifestyle creators",
                "health wellness creators",
                "family lifestyle creators",
            ]
        return []

    @classmethod
    def _strategy_search_terms(cls, strategy: Dict[str, Any]) -> List[str]:
        terms: List[str] = []
        creator = strategy.get("creator_strategy") or {}
        cls._collect_terms(terms, strategy.get("preferred_niches"))
        cls._collect_terms(terms, creator.get("preferred_niches"))
        cls._collect_terms(terms, strategy.get("interests"))
        for item in strategy.get("content_strategy") or []:
            if isinstance(item, dict):
                cls._collect_terms(terms, item.get("content_type"))
            else:
                cls._collect_terms(terms, item)
        for item in strategy.get("discovery_priorities") or []:
            factor = item.get("factor") if isinstance(item, dict) else item
            if isinstance(factor, str) and factor.strip().lower() not in _GENERIC_PRIORITY_WORDS:
                cls._collect_terms(terms, factor)
        return terms

    @classmethod
    def _strategy_locations(cls, strategy: Dict[str, Any]) -> List[str]:
        creator = strategy.get("creator_strategy") or {}
        locations: List[str] = []
        cls._collect_terms(locations, creator.get("preferred_locations"))
        cls._collect_terms(locations, strategy.get("preferred_locations"))
        return locations

    @staticmethod
    def _collect_terms(bucket: List[str], value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            text = value.strip()
            if text and text not in bucket:
                bucket.append(text)
            return
        if isinstance(value, dict):
            for key in ("niche", "name", "label", "content_type", "factor"):
                if value.get(key):
                    CampaignQueryBuilder._collect_terms(bucket, value.get(key))
            return
        if isinstance(value, Iterable) and not isinstance(value, (bytes, bytearray)):
            for item in value:
                CampaignQueryBuilder._collect_terms(bucket, item)
