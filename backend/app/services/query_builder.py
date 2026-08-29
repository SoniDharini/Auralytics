from typing import Any, Dict, Iterable, List, Optional
import re
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

        def compose(term: str, extra: str = "") -> str:
            term = cls.clean_keyword(term)
            extra = cls.clean_keyword(extra) if extra else ""
            if not term:
                return ""
            parts = [p for p in (term, extra, location) if p]
            return " ".join(parts).strip()

        queries: List[str] = []

        def push(value: str) -> None:
            if value and value not in queries:
                queries.append(value)

        # 1. Explicit discovery keywords carry the strongest intent.
        for keyword in campaign.keywords or []:
            push(compose(keyword))
            if len(queries) < max_queries:
                for intent in intents[:2]:
                    push(compose(keyword, intent))
            if len(queries) < max_queries and "review" in intents:
                push(compose(keyword, "reviewer"))

        # 2. Audience interests / niches from the campaign brief (user requirements first).
        for interest in campaign.interests or []:
            push(compose(interest))
            if len(queries) < max_queries:
                for intent in intents[:1]:
                    push(compose(interest, intent))

        # 3. Strategy niches from the Strategy Agent (handoff, not user re-entry).
        for niche in cls._strategy_search_terms(strategy or {}):
            push(compose(niche))
            if len(queries) < max_queries:
                for intent in intents[:1]:
                    push(compose(niche, intent))

        # 4. Campaign type as a topical hint.
        for campaign_type in campaign.campaign_types or []:
            push(compose(campaign_type))

        # 5. Thematic words from the campaign name, only if we still need queries.
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
