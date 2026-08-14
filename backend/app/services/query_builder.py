from typing import List, Optional
import re
from app.models.campaign import Campaign


class CampaignQueryBuilder:
    """Builds targeted search queries for social platform discovery from campaign brief."""

    @staticmethod
    def clean_keyword(text: str) -> str:
        return re.sub(r"[^\w\s-]", "", text).strip()

    @classmethod
    def build_queries(cls, campaign: Campaign, max_queries: int = 5) -> List[str]:
        queries: List[str] = []

        # 1. Primary location keyword
        location = "India"
        if campaign.target_locations:
            parts = [cls.clean_keyword(p) for p in campaign.target_locations.split(",") if p.strip()]
            if parts:
                location = parts[0]

        # 2. Interest / Niche based queries
        interests = campaign.interests or []
        for interest in interests:
            cleaned = cls.clean_keyword(interest)
            if cleaned:
                q1 = f"{cleaned} {location}".strip()
                if q1 not in queries:
                    queries.append(q1)

        # 3. Campaign Name / Brand context
        if campaign.name:
            # Extract key thematic words (e.g. Skincare, Summer, Glow, Launch)
            words = [cls.clean_keyword(w) for w in campaign.name.split() if len(w) > 3]
            if words:
                q2 = f"{' '.join(words[:2])} {location} creators".strip()
                if q2 not in queries:
                    queries.append(q2)

        # 4. Fallback queries if list is small
        if len(queries) < 2 and campaign.brand:
            queries.append(f"{campaign.brand} {location}")
        if len(queries) < 2 and campaign.objective:
            queries.append(f"{campaign.objective} {location} creators")

        if not queries:
            queries = [f"Beauty Skincare {location}", f"Lifestyle {location}"]

        return queries[:max_queries]
