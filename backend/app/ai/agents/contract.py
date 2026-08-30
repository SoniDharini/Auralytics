"""Contract Agent — generates contract terms, risk analysis, and draft agreements for accepted creators."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.agents.base import SECURITY_RULE, MISSING_DATA_RULE, AgentContext, BaseAgent
from app.ai.schemas import AgentResultEnvelope
from app.ai.workflow_states import AgentNames
from app.core.exceptions import AgentValidationException
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.campaign_strategy import CampaignStrategy
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage

logger = logging.getLogger(__name__)


class ContractAgentOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contract_title: str = Field(default="Influencer Collaboration Agreement")
    creator_name: str
    creator_username: str
    campaign_name: str
    agreed_value: float = Field(ge=0, description="Final agreed collaboration fee")
    currency: str = "INR"
    start_date: str = Field(default="Campaign Launch Date")
    end_date: str = Field(default="30 Days Post Launch")
    payment_due: str = Field(default="Net 30 post delivery")
    risk_level: str = Field(default="LOW", description="LOW | MEDIUM | HIGH")
    deliverables: List[str] = Field(default_factory=list)
    usage_rights: str = Field(default="Digital & social media usage across brand channels for 12 months")
    exclusivity: str = Field(default="Non-exclusive within brand category during campaign flight")
    additional_terms: Optional[str] = Field(default="")
    contract_body: Optional[str] = Field(default="")
    ai_risks: List[str] = Field(default_factory=list)
    missing_clauses: List[str] = Field(default_factory=list)
    summary_terms: str = Field(default="")
    confidence: float = Field(default=0.95, ge=0, le=1)

    @field_validator("deliverables", "ai_risks", "missing_clauses", mode="before")
    @classmethod
    def coerce_contract_lists(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(i) for i in v]
        return [str(v)]

    @field_validator("agreed_value", mode="before")
    @classmethod
    def parse_numeric(cls, v: Any) -> float:
        try:
            return float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("agreed_value must be numeric") from exc

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        try:
            val = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be numeric") from exc
        if val > 1 and val <= 100:
            val = val / 100.0
        return max(0.0, min(1.0, val))


class ContractAgent(BaseAgent):
    name = AgentNames.CONTRACT
    version = "1.1.0"
    description = (
        "Drafts commercial agreements and performs AI risk analysis for accepted creators using finalized terms."
    )

    def validate_input(self, ctx: AgentContext) -> None:
        super().validate_input(ctx)
        target_inf_id = ctx.extras.get("influencer_id")
        agreed_terms = ctx.extras.get("agreed_terms") or {}

        # Contract readiness checks
        if not target_inf_id and not agreed_terms.get("influencer_id"):
            raise AgentValidationException(
                detail="CONTRACT_INFORMATION_REQUIRED: An influencer must be selected for contract generation."
            )

    async def build_context(self, ctx: AgentContext) -> Dict[str, Any]:
        campaign = ctx.campaign
        target_inf_id = ctx.extras.get("influencer_id")
        provided_terms = ctx.extras.get("agreed_terms") or {}

        stmt = (
            select(CampaignInfluencer)
            .options(selectinload(CampaignInfluencer.influencer))
            .where(CampaignInfluencer.campaign_id == campaign.id)
        )
        if target_inf_id:
            stmt = stmt.where(CampaignInfluencer.influencer_id == target_inf_id)

        links_res = await ctx.db.execute(stmt)
        links = links_res.scalars().all()

        if not links:
            raise AgentValidationException(
                detail="CONTRACT_INFORMATION_REQUIRED: Creator is not associated with this campaign."
            )

        # Creator must be ACCEPTED
        accepted_link = None
        for link in links:
            if link.status in (CampaignInfluencerStatus.ACCEPTED, "ACCEPTED"):
                accepted_link = link
                break
        if not accepted_link and links:
            accepted_link = links[0]

        if accepted_link.status not in (CampaignInfluencerStatus.ACCEPTED, "ACCEPTED"):
            raise AgentValidationException(
                detail=f"CONTRACT_GATE: Creator status is '{accepted_link.status}'. Only ACCEPTED creators can proceed to Contract stage."
            )

        influencer = accepted_link.influencer
        if not influencer:
            raise AgentValidationException(detail="Creator details not found in database")

        # Load outreach messages & extracted terms if present
        msg_stmt = (
            select(OutreachMessage)
            .where(
                OutreachMessage.campaign_id == campaign.id,
                OutreachMessage.influencer_id == influencer.id,
            )
            .order_by(OutreachMessage.created_at.desc())
            .limit(1)
        )
        msg_res = await ctx.db.execute(msg_stmt)
        last_outreach = msg_res.scalar_one_or_none()

        extracted_terms = (last_outreach.extracted_terms or {}) if last_outreach else {}
        merged_terms = {**extracted_terms, **provided_terms}

        agreed_rate = (
            last_outreach.final_amount if last_outreach and last_outreach.final_amount
            else (
                merged_terms.get("agreed_rate")
                or merged_terms.get("final_amount")
                or merged_terms.get("creator_requested_price")
                or merged_terms.get("rate")
                or merged_terms.get("value")
            )
        )

        if not agreed_rate or float(agreed_rate) <= 0:
            raise AgentValidationException(
                detail="CONTRACT_INFORMATION_REQUIRED: Final agreed rate is required before contract generation. Please save collaboration details first."
            )

        deliverables = (
            last_outreach.deliverables if last_outreach and last_outreach.deliverables
            else merged_terms.get("deliverables")
        ) or ["Dedicated collaboration video/content as agreed"]

        timeline_start = (
            last_outreach.timeline_start if last_outreach and last_outreach.timeline_start
            else merged_terms.get("timeline_start") or campaign.start_date or "Launch Date"
        )
        timeline_end = (
            last_outreach.timeline_end if last_outreach and last_outreach.timeline_end
            else merged_terms.get("timeline_end") or campaign.end_date or "Launch + 30"
        )
        currency = (
            last_outreach.currency if last_outreach and last_outreach.currency
            else merged_terms.get("currency") or "INR"
        )
        additional_terms = (
            last_outreach.additional_terms if last_outreach and last_outreach.additional_terms
            else merged_terms.get("additional_terms") or ""
        )

        # Discovery context
        discovery_reason = "High content relevance and audience engagement."
        for match_block in (accepted_link.match_reasons or []):
            if match_block.get("recommendation_reason"):
                discovery_reason = match_block["recommendation_reason"]
                break

        outreach_pitch = (last_outreach.body or last_outreach.short_dm) if last_outreach else "Standard collaboration pitch"

        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "brand_name": campaign.brand,
            "campaign_objective": campaign.objective,
            "product_description": campaign.description or "Brand promotional campaign",
            "influencer": {
                "influencer_id": influencer.id,
                "name": influencer.name,
                "username": influencer.username,
                "platform": influencer.platform,
                "profile_url": influencer.profile_url or f"https://{influencer.platform}.com/{influencer.username}",
                "niches": influencer.niches or [],
            },
            "discovery_data": {
                "recommendation_reason": discovery_reason,
                "match_score": accepted_link.match_score or 90.0,
            },
            "outreach_data": {
                "subject": last_outreach.subject if last_outreach else "Collaboration Request",
                "pitch": outreach_pitch,
            },
            "negotiated_terms": {
                "agreed_rate": float(agreed_rate),
                "currency": currency,
                "deliverables": deliverables,
                "timeline_start": timeline_start,
                "timeline_end": timeline_end,
                "additional_terms": additional_terms,
                "usage_rights": merged_terms.get("usage_rights") or "Digital & social media usage for 12 months",
                "exclusivity": merged_terms.get("exclusivity") or "Non-exclusive within brand category during campaign flight",
                "payment_terms": merged_terms.get("payment_terms") or "Net 30 upon delivery and verification",
            },
            "outreach_id": last_outreach.id if last_outreach else None,
        }

    def build_system_prompt(self, ctx: AgentContext) -> str:
        return "\n".join(
            [
                "You are the Contract Agent of Auralytics.",
                "Your responsibility is to transform confirmed collaboration terms into a professional influencer marketing contract draft.",
                "The campaign, influencer, and commercial information provided by Auralytics is authoritative.",
                "You may improve wording, structure, and formal legal phrasing.",
                "CRITICAL COMMERCIAL TERM PROTECTION RULES:",
                "- You MUST NOT change the final collaboration amount.",
                "- You MUST NOT change the currency.",
                "- You MUST NOT change the agreed deliverables.",
                "- You MUST NOT change the agreed timeline.",
                "- You MUST NOT change approved additional terms.",
                "- Do NOT invent unsupplied facts, fake bank details, or claim that the contract is already signed.",
                "Generate a professional contract_body containing full agreement clauses (Parties, Scope of Work, Deliverables, Compensation, Rights & Ownership, Confidentiality, Termination).",
                "Analyze the terms for operational risks in ai_risks and note missing clauses in missing_clauses.",
                "Return structured JSON matching ContractAgentOutput only.",
                MISSING_DATA_RULE,
                SECURITY_RULE,
            ]
        )

    def build_user_prompt(self, ctx: AgentContext, context_payload: Dict[str, Any]) -> str:
        inf = context_payload["influencer"]
        terms = context_payload["negotiated_terms"]
        return (
            f"Draft the formal Influencer Collaboration Agreement for:\n"
            f"Creator: {inf['name']} (@{inf['username']}) on {inf['platform']}\n"
            f"Brand: {context_payload['brand_name']} | Campaign: {context_payload['campaign_name']}\n"
            f"Objective: {context_payload['campaign_objective']}\n\n"
            f"CONFIRMED COMMERCIAL TERMS:\n"
            f"- Compensation: {terms['currency']} {terms['agreed_rate']:,.2f}\n"
            f"- Deliverables: {', '.join(terms['deliverables'])}\n"
            f"- Timeline: {terms['timeline_start']} to {terms['timeline_end']}\n"
            f"- Additional Terms: {terms['additional_terms'] or 'None'}\n"
            f"- Usage Rights: {terms['usage_rights']}\n"
            f"- Exclusivity: {terms['exclusivity']}\n"
            f"- Payment Due: {terms['payment_terms']}\n\n"
            f"Context Summary:\n{json.dumps(context_payload, indent=2)}"
        )

    async def call_llm(
        self,
        ctx: AgentContext,
        system_prompt: str,
        user_prompt: str,
        context_payload: Dict[str, Any],
    ) -> AgentResultEnvelope:
        structured, raw = await self.llm.generate_structured_with_meta(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=ContractAgentOutput,
            temperature=0.2,
            max_tokens=3000,
        )
        data = structured.model_dump()
        inf = context_payload.get("influencer") or {}
        terms = context_payload.get("negotiated_terms") or {}

        # Commercial Term Protection: Authoritative user terms strictly overwrite/guarantee compliance
        data["influencer_id"] = inf.get("influencer_id")
        data["creator_name"] = inf.get("name") or "Creator"
        data["creator_username"] = inf.get("username") or "creator"
        data["campaign_name"] = context_payload.get("campaign_name") or ctx.campaign.name
        data["agreed_value"] = float(terms.get("agreed_rate") or data.get("agreed_value") or 0.0)
        data["currency"] = str(terms.get("currency") or "INR")
        data["deliverables"] = list(terms.get("deliverables") or data.get("deliverables") or [])
        data["start_date"] = str(terms.get("timeline_start") or data.get("start_date") or "")
        data["end_date"] = str(terms.get("timeline_end") or data.get("end_date") or "")
        data["additional_terms"] = str(terms.get("additional_terms") or "")
        data["outreach_id"] = context_payload.get("outreach_id")

        if not data.get("contract_body"):
            data["contract_body"] = (
                f"INFLUENCER COLLABORATION AGREEMENT\n\n"
                f"This Agreement is entered into between {context_payload.get('brand_name')} ('Brand') "
                f"and {data['creator_name']} (@{data['creator_username']}) ('Creator') for the campaign '{data['campaign_name']}'.\n\n"
                f"1. DELIVERABLES:\n" + "\n".join(f" - {d}" for d in data['deliverables']) + "\n\n"
                f"2. COMPENSATION:\n Total Fee of {data['currency']} {data['agreed_value']:,.2f} payable {data['payment_due']}.\n\n"
                f"3. TIMELINE:\n Active flight dates from {data['start_date']} through {data['end_date']}.\n\n"
                f"4. USAGE RIGHTS & EXCLUSIVITY:\n {data['usage_rights']}. {data['exclusivity']}.\n\n"
                f"5. ADDITIONAL TERMS:\n {data['additional_terms'] or 'Standard collaboration terms apply.'}"
            )

        summary = f"Generated contract specification for {data['creator_name']} (@{data['creator_username']}) — Value: {data['currency']} {data['agreed_value']:,.2f}"
        return AgentResultEnvelope(
            status="COMPLETED",
            summary=summary,
            confidence=structured.confidence,
            recommendations=[data],
            requires_approval=True,
            data=data,
            provider=raw.provider,
            model=raw.model,
            provider_latency_ms=raw.latency_ms,
            grok_called=True,
        )

    async def validate_output(
        self,
        ctx: AgentContext,
        result: AgentResultEnvelope,
        context_payload: Dict[str, Any],
    ) -> AgentResultEnvelope:
        data = result.data or {}
        terms = context_payload.get("negotiated_terms") or {}
        
        # Enforce Commercial Term Protection
        expected_rate = float(terms.get("agreed_rate") or 0)
        if expected_rate <= 0:
            raise AgentValidationException(detail="Contract validation failed: final collaboration amount must be greater than 0")

        data["agreed_value"] = expected_rate
        data["currency"] = str(terms.get("currency") or "INR")
        data["deliverables"] = list(terms.get("deliverables") or [])
        data["start_date"] = str(terms.get("timeline_start") or "")
        data["end_date"] = str(terms.get("timeline_end") or "")

        result.data = data
        return result
