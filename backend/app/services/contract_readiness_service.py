"""Contract Readiness Service — deterministic validation of creator contract readiness and pre-contract terms assembly."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.contract import Contract
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage
from app.models.user import User

logger = logging.getLogger(__name__)


class ContractReadinessResult:
    def __init__(
        self,
        ready: bool,
        status: str,
        missing_fields: Optional[List[str]] = None,
        blocking_reason: Optional[str] = None,
        final_terms: Optional[Dict[str, Any]] = None,
        suggested_terms: Optional[Dict[str, Any]] = None,
        creator_name: Optional[str] = None,
        creator_username: Optional[str] = None,
        outreach_status: Optional[str] = None,
        shortlist_status: Optional[str] = None,
        contract_id: Optional[str] = None,
    ) -> None:
        self.ready = ready
        self.status = status
        self.missing_fields = missing_fields or []
        self.blocking_reason = blocking_reason
        self.final_terms = final_terms or {}
        self.suggested_terms = suggested_terms or {}
        self.creator_name = creator_name
        self.creator_username = creator_username
        self.outreach_status = outreach_status
        self.shortlist_status = shortlist_status
        self.contract_id = contract_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ready": self.ready,
            "status": self.status,
            "missing_fields": self.missing_fields,
            "blocking_reason": self.blocking_reason,
            "final_terms": self.final_terms,
            "suggested_terms": self.suggested_terms,
            "creator_name": self.creator_name,
            "creator_username": self.creator_username,
            "outreach_status": self.outreach_status,
            "shortlist_status": self.shortlist_status,
            "contract_id": self.contract_id,
        }


class ContractReadinessService:
    """Evaluates whether an influencer collaboration is ready for Contract Agent without LLM calls."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_readiness(
        self,
        *,
        campaign_id: str,
        influencer_id: str,
        user: User,
    ) -> ContractReadinessResult:
        # 1. Verify Campaign ownership
        camp_stmt = select(Campaign).where(Campaign.id == campaign_id, Campaign.owner_id == user.id)
        camp_res = await self.db.execute(camp_stmt)
        campaign = camp_res.scalar_one_or_none()
        if not campaign:
            raise NotFoundException(detail="Campaign not found or access denied")

        # 2. Verify CampaignInfluencer association
        link_stmt = (
            select(CampaignInfluencer)
            .options(selectinload(CampaignInfluencer.influencer))
            .where(
                CampaignInfluencer.campaign_id == campaign_id,
                CampaignInfluencer.influencer_id == influencer_id,
            )
        )
        link_res = await self.db.execute(link_stmt)
        link = link_res.scalar_one_or_none()
        if not link:
            return ContractReadinessResult(
                ready=False,
                status="NOT_APPLICABLE",
                blocking_reason="Creator is not associated with this campaign.",
            )

        creator_name = link.influencer.name if link.influencer else "Creator"
        creator_username = link.influencer.username if link.influencer else "creator"
        shortlist_status = link.status

        # 3. Check for existing Contract
        cntr_stmt = select(Contract).where(
            Contract.campaign_id == campaign_id,
            Contract.influencer_id == influencer_id,
        )
        cntr_res = await self.db.execute(cntr_stmt)
        existing_contract = cntr_res.scalar_one_or_none()
        contract_id = existing_contract.id if existing_contract else None

        # 4. Check Shortlist / Outreach Status
        if link.status in (CampaignInfluencerStatus.DECLINED, CampaignInfluencerStatus.REJECTED, "DECLINED", "REJECTED"):
            return ContractReadinessResult(
                ready=False,
                status="NOT_APPLICABLE",
                blocking_reason="Influencer declined the collaboration. Contract is not applicable.",
                creator_name=creator_name,
                creator_username=creator_username,
                shortlist_status=link.status,
                contract_id=contract_id,
            )

        if link.status in (CampaignInfluencerStatus.NEGOTIATING, "NEGOTIATING"):
            return ContractReadinessResult(
                ready=False,
                status="LOCKED",
                blocking_reason="Complete negotiation before creating a contract.",
                creator_name=creator_name,
                creator_username=creator_username,
                shortlist_status=link.status,
                outreach_status="NEGOTIATING",
                contract_id=contract_id,
            )

        # 5. Inspect OutreachMessage
        msg_stmt = (
            select(OutreachMessage)
            .where(
                OutreachMessage.campaign_id == campaign_id,
                OutreachMessage.influencer_id == influencer_id,
            )
            .order_by(OutreachMessage.created_at.desc())
            .limit(1)
        )
        msg_res = await self.db.execute(msg_stmt)
        last_outreach = msg_res.scalar_one_or_none()

        outreach_status = last_outreach.status if last_outreach else "NOT_CONTACTED"
        response_status = last_outreach.response_status if last_outreach else "PENDING_RESPONSE"

        # Check if Outreach is accepted
        is_accepted = (
            link.status in (CampaignInfluencerStatus.ACCEPTED, "ACCEPTED")
            or outreach_status == "ACCEPTED"
            or response_status == "ACCEPTED"
        )

        if not is_accepted:
            return ContractReadinessResult(
                ready=False,
                status="LOCKED",
                blocking_reason=f"Outreach must be accepted before contract generation (current status: {outreach_status}).",
                creator_name=creator_name,
                creator_username=creator_username,
                shortlist_status=link.status,
                outreach_status=outreach_status,
                contract_id=contract_id,
            )

        # 6. Extract Authoritative Final Negotiated Terms
        extracted = (last_outreach.extracted_terms or {}) if last_outreach else {}
        agreed_rate = (
            last_outreach.final_amount
            if last_outreach and last_outreach.final_amount is not None and last_outreach.final_amount > 0
            else (
                extracted.get("agreed_rate")
                or extracted.get("final_amount")
                or extracted.get("creator_requested_price")
                or extracted.get("rate")
                or extracted.get("value")
            )
        )
        currency = (
            last_outreach.currency
            if last_outreach and last_outreach.currency
            else extracted.get("currency") or "INR"
        )
        deliverables = (
            last_outreach.deliverables
            if last_outreach and last_outreach.deliverables
            else extracted.get("deliverables")
        ) or []

        timeline_start = (
            last_outreach.timeline_start
            if last_outreach and last_outreach.timeline_start
            else extracted.get("timeline_start") or campaign.start_date or "Launch Date"
        )
        timeline_end = (
            last_outreach.timeline_end
            if last_outreach and last_outreach.timeline_end
            else extracted.get("timeline_end") or campaign.end_date or "Launch + 30"
        )
        additional_terms = (
            last_outreach.additional_terms
            if last_outreach and last_outreach.additional_terms
            else extracted.get("additional_terms") or ""
        )

        final_terms = {
            "agreed_rate": float(agreed_rate) if agreed_rate and float(agreed_rate) > 0 else None,
            "currency": currency,
            "deliverables": deliverables if isinstance(deliverables, list) else [deliverables],
            "timeline_start": timeline_start,
            "timeline_end": timeline_end,
            "additional_terms": additional_terms,
            "usage_rights": extracted.get("usage_rights") or "3 Months Organic",
            "exclusivity": extracted.get("exclusivity") or "Non-exclusive",
            "payment_terms": extracted.get("payment_terms") or "50% Advance, 50% Completion",
        }

        # 7. Check for Missing Commercial Terms
        missing_fields: List[str] = []
        if not final_terms["agreed_rate"]:
            missing_fields.append("agreed_rate")
        if not final_terms["deliverables"] or len(final_terms["deliverables"]) == 0:
            missing_fields.append("deliverables")

        if missing_fields:
            return ContractReadinessResult(
                ready=False,
                status="CONTRACT_INFORMATION_REQUIRED",
                missing_fields=missing_fields,
                blocking_reason=f"Required commercial terms missing ({', '.join(missing_fields)}). Confirm terms in Outreach.",
                final_terms=final_terms,
                creator_name=creator_name,
                creator_username=creator_username,
                outreach_status=outreach_status,
                shortlist_status=link.status,
                contract_id=contract_id,
            )

        # 8. Assemble structured suggested terms with deterministic 50/50 payment calculations
        rate_val = float(final_terms["agreed_rate"] or 0.0)
        advance_val = round(rate_val * 0.5, 2)
        balance_val = round(rate_val - advance_val, 2)

        suggested_terms = {
            "influencer_id": influencer_id,
            "campaign_id": campaign_id,
            "creator_name": creator_name,
            "creator_username": creator_username,
            "campaign_name": campaign.name,
            "brand_name": campaign.brand,
            "compensation": {
                "total": rate_val,
                "currency": currency,
            },
            "payment": {
                "structure": "50_50",
                "advance_percentage": 50.0,
                "advance_amount": advance_val,
                "balance_percentage": 50.0,
                "balance_amount": balance_val,
                "method": "Bank Transfer",
                "balance_due_days": 7,
                "terms_text": (
                    f"{currency} {advance_val:,.2f} (50%) advance payable upon execution; "
                    f"remaining {currency} {balance_val:,.2f} (50%) payable via Bank Transfer within 7 days of completion."
                ),
            },
            "deliverables": final_terms["deliverables"] if len(final_terms["deliverables"]) > 0 else ["1 Dedicated collaboration video"],
            "timeline": {
                "start_date": timeline_start,
                "end_date": timeline_end,
                "draft_submission_deadline": "3 days prior to publishing",
                "publishing_deadline": timeline_start,
            },
            "revisions": {
                "allowed_rounds": 2,
                "scope": "Factual accuracy, brand guidelines, approved product claims, and agreed brief requirements.",
            },
            "approval": {
                "pre_publication_required": True,
                "review_window_days": 3,
            },
            "product_claims": {
                "policy": "BRAND_APPROVED_ONLY",
                "claim_guidelines": "Creator shall not make unapproved efficacy, performance, medical, or comparative product claims.",
            },
            "usage_rights": {
                "organic_reposting": True,
                "paid_ads": False,
                "website_use": True,
                "duration": "3 Months",
                "territory": "India",
            },
            "ownership": {
                "copyright_owner": "INFLUENCER",
                "license_grant": "Influencer retains copyright and grants Brand a non-exclusive license as specified in Usage Rights.",
            },
            "exclusivity": {
                "required": False,
                "category": campaign.name or "Competitor Products",
                "duration_days": 30,
                "scope": "No direct competitor promotions during the exclusivity window.",
            },
            "cancellation": {
                "brand_cancellation": "Brand may cancel prior to draft creation with payment for work performed to date. Advance is refundable if no work commenced.",
                "influencer_cancellation": "Creator cancellation requires full refund of any advance received and return of gifted products.",
                "force_majeure": "Neither party liable for failure due to unforeseen events beyond reasonable control.",
            },
            "termination": {
                "grounds": [
                    "Material breach of agreement terms",
                    "Failure to deliver content by agreed deadline",
                    "Publication without required brand pre-approval",
                    "Violation of brand safety or product claim guidelines",
                ],
            },
            "additional_terms": additional_terms,
        }

        # 9. All terms present and verified
        return ContractReadinessResult(
            ready=True,
            status="READY",
            missing_fields=[],
            blocking_reason=None,
            final_terms=final_terms,
            suggested_terms=suggested_terms,
            creator_name=creator_name,
            creator_username=creator_username,
            outreach_status=outreach_status,
            shortlist_status=link.status,
            contract_id=contract_id,
        )

    async def list_campaign_creators_readiness(
        self,
        *,
        campaign_id: str,
        user: User,
    ) -> List[Dict[str, Any]]:
        """Return readiness info for all creators linked to this campaign."""
        camp_stmt = select(Campaign).where(Campaign.id == campaign_id, Campaign.owner_id == user.id)
        camp_res = await self.db.execute(camp_stmt)
        campaign = camp_res.scalar_one_or_none()
        if not campaign:
            raise NotFoundException(detail="Campaign not found")

        link_stmt = (
            select(CampaignInfluencer)
            .options(selectinload(CampaignInfluencer.influencer))
            .where(CampaignInfluencer.campaign_id == campaign_id)
        )
        link_res = await self.db.execute(link_stmt)
        links = link_res.scalars().all()

        results = []
        for link in links:
            readiness = await self.check_readiness(
                campaign_id=campaign_id,
                influencer_id=link.influencer_id,
                user=user,
            )
            data = readiness.to_dict()
            data["influencer_id"] = link.influencer_id
            results.append(data)

        return results
