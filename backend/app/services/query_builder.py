from typing import List, Optional
import re
from app.models.campaign import Campaign

# Words that add no discovery signal on their own.
_NOISE_WORDS = {
    "the", "and", "for", "with", "your", "our", "from", "into", "this", "that",
    "campaign", "launch", "new", "best", "top", "phase", "season",
}


class CampaignQueryBuilder:
    """Builds targeted search queries for social platform discovery from a campaign brief.

    Queries are derived purely from campaign fields. Nothing is hardcoded, and the
    set is deliberately small because each YouTube search costs 100 quota units.
    """

    @staticmethod
    def clean_keyword(text: str) -> str:
        return re.sub(r"[^\w\s-]", "", str(text)).strip()

    @classmethod
    def resolve_location(cls, campaign: Campaign) -> Optional[str]:
        if not campaign.target_locations:
            return None
        parts = [cls.clean_keyword(p) for p in campaign.target_locations.split(",") if p.strip()]
        return parts[0] if parts else None

    @classmethod
    def build_queries(cls, campaign: Campaign, max_queries: int = 5) -> List[str]:
        location = cls.resolve_location(campaign)

        def compose(term: str) -> str:
            term = cls.clean_keyword(term)
            if not term:
                return ""
            return f"{term} {location}".strip() if location else term

        queries: List[str] = []

        def push(value: str) -> None:
            if value and value not in queries:
                queries.append(value)

        # 1. Explicit discovery keywords carry the strongest intent.
        for keyword in campaign.keywords or []:
            push(compose(keyword))

        # 2. Audience interests / niches.
        for interest in campaign.interests or []:
            push(compose(interest))

        # 3. Campaign type as a topical hint.
        for campaign_type in campaign.campaign_types or []:
            push(compose(campaign_type))

        # 4. Thematic words from the campaign name, only if we still need queries.
        if len(queries) < max_queries and campaign.name:
            words = [
                cls.clean_keyword(w)
                for w in campaign.name.split()
                if len(w) > 3 and w.lower() not in _NOISE_WORDS
            ]
            words = [w for w in words if w]
            if words:
                push(compose(" ".join(words[:2])))

        # 5. Last resort: brand or objective context.
        if not queries and campaign.brand:
            push(compose(campaign.brand))
        if not queries and campaign.objective:
            push(compose(campaign.objective))

        # An empty list is a valid outcome; the caller surfaces a "brief too thin"
        # error rather than inventing a niche to search for.
        return queries[:max_queries]
