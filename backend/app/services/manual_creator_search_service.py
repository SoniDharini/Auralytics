"""Manual YouTube creator search for an existing campaign.

Reuses the current YouTube provider, creator upsert, scoring, entity classification,
and requirement gates. Does not rerun Discovery Agent ranking.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.audience_profile import PERSONA_ADULT, PERSONA_GEN_Z, PERSONA_MATURE, PERSONA_UNKNOWN
from app.ai.creator_entity import (
    ORGANIZATION_ENTITIES,
    classify_creator_entity,
    is_collaborable_entity,
    rural_persona_mismatch_score,
)
from app.ai.creator_tiers import display_tier_key, tier_for_followers
from app.ai.discovery_requirements import build_discovery_requirements, eligibility_for_creator
from app.ai.trend_signals import compute_trend_signals
from app.core.config import settings
from app.core.exceptions import (
    ConflictException,
    InvalidRequestException,
    ProviderNotConfiguredException,
)
from app.integrations.youtube.client import YouTubeAPIError
from app.integrations.youtube.mapper import map_youtube_channel_to_creator
from app.integrations.youtube.schemas import YouTubeChannelItem
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.influencer import Influencer
from app.services.creator_discovery_service import CreatorDiscoveryService, DiscoveryStats, PLATFORM_YOUTUBE
from app.services.creator_scoring_service import (
    CreatorScoringService,
    CreatorSignals,
    build_campaign_terms,
    resolve_target_country,
)
from app.services.youtube_query import parse_manual_creator_query

logger = logging.getLogger(__name__)

_GEN_Z_CONTENT = (
    "comedy", "gaming", "vlog", "roast", "meme", "college", "campus",
    "fashion", "lifestyle", "entertainment", "music", "pop culture", "gen z",
)
_ADULT_CONTENT = (
    "finance", "career", "business", "parent", "professional", "invest",
    "automobile", "travel", "health",
)
_MATURE_CONTENT = ("retirement", "senior", "family", "health wellness", "mature")

SELECTION_SOURCE = "MANUAL_SEARCH"


class ManualCreatorSearchService:
    def __init__(self, discovery: Optional[CreatorDiscoveryService] = None):
        self.discovery = discovery or CreatorDiscoveryService()

    async def search(
        self,
        db: AsyncSession,
        campaign: Campaign,
        query: str,
        *,
        limit: int = 8,
    ) -> Dict[str, Any]:
        try:
            parsed = parse_manual_creator_query(query)
        except ValueError as exc:
            raise InvalidRequestException(detail=str(exc)) from exc

        if not self.discovery.youtube.is_configured():
            raise ProviderNotConfiguredException(
                "YouTube Data API is not configured on the server. Add YOUTUBE_API_KEY to the backend environment."
            )

        strategy_json = await self.discovery._load_strategy_json(db, campaign.id)
        reqs = build_discovery_requirements(campaign, strategy_json)
        region = resolve_target_country(campaign)

        try:
            channels = await self.discovery.youtube.resolve_manual_query(
                parsed,
                region_code=region,
                max_results=max(1, min(int(limit), 10)),
            )
        except YouTubeAPIError as exc:
            raise self.discovery._translate_provider_error(exc) from exc

        results: List[Dict[str, Any]] = []
        for channel in channels:
            try:
                evaluated = await self._evaluate_channel(
                    db, campaign, reqs, channel, parsed.original
                )
            except YouTubeAPIError as exc:
                raise self.discovery._translate_provider_error(exc) from exc
            results.append(evaluated)

        message = None if results else "No YouTube creator was found for this search."
        logger.info(
            "Manual creator search campaign=%s kind=%s raw_hits=%s returned=%s",
            campaign.id,
            parsed.kind,
            len(channels),
            len(results),
        )
        return {
            "campaign_id": campaign.id,
            "query": parsed.original,
            "query_kind": parsed.kind,
            "count": len(results),
            "results": results,
            "message": message,
        }

    async def shortlist(
        self,
        db: AsyncSession,
        campaign: Campaign,
        user,
        *,
        channel_id: str,
        confirm_override: bool = False,
        query: Optional[str] = None,
    ) -> Tuple[CampaignInfluencer, Dict[str, Any]]:
        channel_id = (channel_id or "").strip()
        if not channel_id:
            raise InvalidRequestException(detail="A YouTube channel ID is required to shortlist.")

        if not self.discovery.youtube.is_configured():
            raise ProviderNotConfiguredException(
                "YouTube Data API is not configured on the server. Add YOUTUBE_API_KEY to the backend environment."
            )

        strategy_json = await self.discovery._load_strategy_json(db, campaign.id)
        reqs = build_discovery_requirements(campaign, strategy_json)

        existing = await self._find_existing_link(db, campaign.id, channel_id)
        if existing and existing.status == CampaignInfluencerStatus.SHORTLISTED:
            return existing, self._evaluation_from_link(existing, query=query)

        try:
            fetched = await self.discovery.youtube.fetch_channels([channel_id])
        except YouTubeAPIError as exc:
            raise self.discovery._translate_provider_error(exc) from exc
        if not fetched:
            raise InvalidRequestException(detail="No YouTube creator was found for this channel ID.")

        evaluation = await self._evaluate_channel(
            db, campaign, reqs, fetched[0], query or channel_id
        )
        if not evaluation.get("shortlist_allowed") and not evaluation.get("already_shortlisted"):
            raise InvalidRequestException(
                detail=(
                    "This appears to be an organization/team channel rather than an individual "
                    "creator. Normal influencer shortlist is not available."
                )
            )
        if evaluation.get("manual_override_required") and not confirm_override:
            raise ConflictException(
                "This creator does not match one or more current Discovery requirements. "
                "Confirm manual override to shortlist anyway. Campaign settings will not be changed."
            )

        influencer = await self._load_influencer(db, channel_id)
        if influencer is None:
            raise InvalidRequestException(detail="Creator data is incomplete and could not be saved.")

        now = datetime.now(timezone.utc)
        match_reasons = list(evaluation.get("match_reasons") or [])
        match_reasons.append(
            {
                "key": "selection_source",
                "label": "Selection source",
                "weight": 0,
                "score": None,
                "available": True,
                "detail": "Manually searched and shortlisted by the user.",
                "source": SELECTION_SOURCE,
                "selection_source": SELECTION_SOURCE,
                "manual_override": bool(evaluation.get("manual_override_required")),
                "override_mismatches": [
                    item.get("code") for item in (evaluation.get("mismatches") or []) if item.get("code")
                ],
            }
        )
        link = await self.discovery._upsert_campaign_link(
            db,
            campaign,
            influencer,
            match_score=evaluation.get("match_score"),
            match_reasons=match_reasons,
            discovery_query=(query or "")[:255] or None,
            now=now,
        )
        link.status = CampaignInfluencerStatus.SHORTLISTED
        influencer.shortlisted = True
        link.influencer = influencer
        await db.flush()
        logger.info(
            "Manual shortlist campaign=%s influencer=%s override=%s user=%s",
            campaign.id,
            influencer.id,
            bool(evaluation.get("manual_override_required")),
            getattr(user, "id", None),
        )
        return link, evaluation

    async def _evaluate_channel(
        self,
        db: AsyncSession,
        campaign: Campaign,
        reqs,
        channel: YouTubeChannelItem,
        query: str,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        video_stats: List[Dict[str, Any]] = []
        try:
            video_stats = await self.discovery.youtube.fetch_recent_video_stats(
                channel,
                max_videos=settings.YOUTUBE_RECENT_VIDEO_SAMPLE,
            )
        except YouTubeAPIError as exc:
            if exc.status_code == 429:
                raise
            logger.debug("Manual search recent videos unavailable for %s: %s", channel.id, exc)

        norm = map_youtube_channel_to_creator(channel, video_stats=video_stats or None)
        titles = [str(v.get("title") or "") for v in (video_stats or []) if v.get("title")]
        entity_type, _hits = classify_creator_entity(
            name=norm.name,
            description=norm.description,
            recent_titles=titles,
        )
        followers = int(norm.followers or 0)
        hidden = followers <= 0
        sample = int(norm.metrics_sample_size or 0)
        views_for_gate = int(norm.avg_views or 0) if sample > 0 else 0
        eligibility, hard_match = eligibility_for_creator(
            platform=norm.platform,
            followers=followers,
            hidden=hidden,
            reqs=reqs,
            country=norm.country,
            location=norm.location,
            entity_type=entity_type,
            recent_avg_views=views_for_gate,
            metrics_sample_size=sample,
            name=norm.name,
        )
        trend = compute_trend_signals(
            followers=followers,
            avg_views=int(norm.avg_views or 0),
            engagement_rate=float(norm.engagement_rate or 0),
            recent_max_views=int((norm.raw_payload or {}).get("recent_max_views") or 0),
            recent_median_views=int((norm.raw_payload or {}).get("recent_median_views") or 0),
            last_upload_at=norm.last_upload_at,
            metrics_sample_size=sample,
        )
        match = CreatorScoringService.score(
            campaign,
            CreatorSignals(
                name=norm.name,
                description=norm.description,
                followers=norm.followers or None,
                engagement_rate=norm.engagement_rate if sample > 0 else None,
                metrics_sample_size=sample,
                last_upload_at=norm.last_upload_at,
                country=norm.country,
                extra_text=" ".join(titles) or None,
            ),
            campaign_terms=build_campaign_terms(campaign),
            target_country=resolve_target_country(campaign),
        )
        persona = self._persona_relevance(reqs, norm.name, norm.description, titles)
        collaborable = is_collaborable_entity(entity_type)
        org_channel = entity_type in ORGANIZATION_ENTITIES or not collaborable
        mismatches = self._mismatch_list(hard_match, reqs, followers, views_for_gate, entity_type)
        if reqs.hard_location and hard_match.get("location") == "UNKNOWN":
            mismatches.append(
                {
                    "code": "LOCATION",
                    "label": "Location",
                    "detail": (
                        f"Channel country is unavailable, so the required location "
                        f"({reqs.hard_location}) cannot be confirmed."
                    ),
                }
            )
        meets = eligibility == "ELIGIBLE" and collaborable and not mismatches
        override_required = (not meets) and collaborable and not org_channel

        influencer = await self.discovery._upsert_influencer(db, norm, now, DiscoveryStats())
        await db.flush()

        link = await self._find_existing_link(db, campaign.id, channel.id)
        campaign_status = link.status if link else None
        already_shortlisted = campaign_status == CampaignInfluencerStatus.SHORTLISTED
        warning = None
        if org_channel:
            warning = "This appears to be an organization/team channel rather than an individual creator."
        elif mismatches:
            warning = (
                "This creator does not satisfy one or more current Discovery requirements. "
                "You can still shortlist them manually. Campaign settings will not be changed."
            )

        from app.schemas.influencer import InfluencerResponse

        return {
            "channel_id": channel.id,
            "influencer_id": influencer.id,
            "link_id": link.id if link else None,
            "campaign_status": campaign_status,
            "already_in_campaign": bool(link),
            "already_recommended": campaign_status == CampaignInfluencerStatus.DISCOVERED,
            "already_shortlisted": already_shortlisted,
            "previously_rejected": campaign_status == CampaignInfluencerStatus.REJECTED,
            "selection_source": SELECTION_SOURCE,
            "creator": InfluencerResponse.model_validate(influencer).model_dump(by_alias=True),
            "entity_type": entity_type,
            "collaboration_suitable": collaborable,
            "shortlist_allowed": (not org_channel) and not already_shortlisted,
            "meets_requirements": meets,
            "manual_override_required": override_required,
            "eligibility": eligibility,
            "requirement_match": hard_match,
            "mismatches": mismatches,
            "warning": warning,
            "tier": display_tier_key(tier_for_followers(followers)) if followers > 0 else "UNKNOWN",
            "match_score": match.score,
            "match_reasons": match.to_payload(),
            "persona_relevance": persona,
            "recent_avg_views": trend.get("recent_avg_views") or (views_for_gate or None),
            "recent_momentum": trend.get("recent_momentum"),
            "auralytics_trend_score": trend.get("auralytics_trend_score"),
            "query": query,
        }

    def _evaluation_from_link(self, link: CampaignInfluencer, query: Optional[str]) -> Dict[str, Any]:
        influencer = link.influencer
        entity_type, _ = classify_creator_entity(
            name=influencer.name, description=influencer.description
        )
        return {
            "channel_id": influencer.external_id,
            "influencer_id": influencer.id,
            "link_id": link.id,
            "campaign_status": link.status,
            "already_in_campaign": True,
            "already_shortlisted": True,
            "selection_source": SELECTION_SOURCE,
            "entity_type": entity_type,
            "shortlist_allowed": False,
            "meets_requirements": True,
            "manual_override_required": False,
            "mismatches": [],
            "warning": None,
            "match_score": link.match_score,
            "query": query,
        }

    @staticmethod
    def _mismatch_list(
        hard_match: Dict[str, str],
        reqs,
        followers: int,
        views: int,
        entity_type: str,
    ) -> List[Dict[str, str]]:
        items: List[Dict[str, str]] = []
        mapping = {
            "location": "LOCATION",
            "creator_tier": "CREATOR_TIER",
            "subscriber_range": "FOLLOWER_RANGE",
            "view_requirement": "VIEW_REQUIREMENT",
            "platform": "PLATFORM",
            "creator_entity": "CREATOR_ENTITY",
        }
        labels = {
            "LOCATION": "Location",
            "CREATOR_TIER": "Creator tier",
            "FOLLOWER_RANGE": "Follower range",
            "VIEW_REQUIREMENT": "View requirement",
            "PLATFORM": "Platform",
            "CREATOR_ENTITY": "Creator type",
        }
        for key, code in mapping.items():
            if hard_match.get(key) != "FAIL":
                continue
            if code == "FOLLOWER_RANGE":
                lo = reqs.hard_subscriber_min
                hi = reqs.hard_subscriber_max
                required = f"{lo or 0:,}–{hi:,}" if hi is not None else f"{lo or 0:,}+"
                detail = f"Creator: {followers:,}. Current requirement: {required}."
            elif code == "VIEW_REQUIREMENT" and reqs.hard_recent_views_min:
                detail = (
                    f"Creator recent average: {views:,}. "
                    f"Current requirement: {int(reqs.hard_recent_views_min):,}."
                )
            elif code == "CREATOR_TIER":
                selected = ", ".join(reqs.hard_creator_tiers) if reqs.hard_creator_tiers else "selected tier"
                detail = f"Creator tier does not match {selected}."
            elif code == "LOCATION":
                detail = f"Required location: {reqs.hard_location}."
            elif code == "CREATOR_ENTITY":
                detail = f"Channel type: {entity_type}."
            else:
                detail = f"{labels[code]} does not match the campaign requirement."
            items.append({"code": code, "label": labels[code], "detail": detail})
        return items

    @staticmethod
    def _persona_relevance(reqs, name: Optional[str], description: Optional[str], titles: List[str]) -> Dict[str, str]:
        target = reqs.audience.persona if reqs.audience else PERSONA_UNKNOWN
        blob = " ".join([str(name or ""), str(description or ""), " ".join(titles)]).lower()
        rural = rural_persona_mismatch_score(name=name, description=description, recent_titles=titles)
        level = "UNKNOWN"
        reason = "No audience analytics were supplied; persona relevance is inferred from observable content only."
        if target == PERSONA_GEN_Z:
            hits = sum(1 for term in _GEN_Z_CONTENT if term in blob)
            if rural >= 2:
                level = "LOW"
                reason = "Recent content is more aligned with rural/traditional themes than the Gen Z persona."
            elif hits >= 2:
                level = "HIGH"
                reason = "Recent titles and channel copy indicate youth/entertainment relevance."
            elif hits == 1:
                level = "MEDIUM"
                reason = "Some observable content overlaps with youth-culture topics."
        elif target == PERSONA_ADULT:
            hits = sum(1 for term in _ADULT_CONTENT if term in blob)
            level = "HIGH" if hits >= 2 else ("MEDIUM" if hits == 1 else "UNKNOWN")
            if hits:
                reason = "Observable content overlaps with adult/professional topics."
        elif target == PERSONA_MATURE:
            hits = sum(1 for term in _MATURE_CONTENT if term in blob)
            level = "HIGH" if hits >= 1 else "UNKNOWN"
            if hits:
                reason = "Observable content overlaps with mature-audience topics."
        return {
            "target": target,
            "level": level,
            "source": "AI_INFERRED" if level != "UNKNOWN" else "UNKNOWN",
            "reason": reason,
        }

    async def _find_existing_link(
        self, db: AsyncSession, campaign_id: str, channel_id: str
    ) -> Optional[CampaignInfluencer]:
        result = await db.execute(
            select(CampaignInfluencer)
            .join(Influencer, CampaignInfluencer.influencer_id == Influencer.id)
            .options(selectinload(CampaignInfluencer.influencer))
            .where(
                CampaignInfluencer.campaign_id == campaign_id,
                Influencer.platform == PLATFORM_YOUTUBE,
                Influencer.external_id == channel_id,
            )
        )
        return result.scalar_one_or_none()

    async def _load_influencer(self, db: AsyncSession, channel_id: str) -> Optional[Influencer]:
        result = await db.execute(
            select(Influencer).where(
                Influencer.platform == PLATFORM_YOUTUBE,
                Influencer.external_id == channel_id,
            )
        )
        return result.scalar_one_or_none()
