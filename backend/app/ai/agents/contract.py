"""Contract Agent — analyzes and drafts complete, professional influencer agreements from confirmed commercial terms."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.ai.agents.base import SECURITY_RULE, MISSING_DATA_RULE, AgentContext, BaseAgent
from app.ai.schemas import AgentResultEnvelope
from app.ai.workflow_states import AgentNames
from app.core.exceptions import AgentValidationException
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage
from app.schemas.contract import ContractTermsPayload
from app.services.contract_readiness_service import ContractReadinessService

logger = logging.getLogger(__name__)


class ContractSectionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key: str
    title: str
    content: str


class ContractAgentOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    contract_title: str = Field(default="Influencer Collaboration Agreement")
    contract_summary: str = Field(default="Complete collaboration agreement synthesized from confirmed commercial terms.")
    parties: Dict[str, str] = Field(default_factory=dict)

    # Structured sections
    sections: List[Dict[str, Any]] = Field(default_factory=list)

    # Commercial term summaries
    commercial_terms: Union[Dict[str, Any], str, Any] = Field(default_factory=dict)
    payment_terms: Union[Dict[str, Any], str, Any] = Field(default_factory=dict)
    usage_rights: Union[Dict[str, Any], str, Any] = Field(default_factory=dict)
    exclusivity: Union[Dict[str, Any], str, Any] = Field(default_factory=dict)
    timeline: Union[Dict[str, Any], str, Any] = Field(default_factory=dict)
    termination: Union[Dict[str, Any], str, Any] = Field(default_factory=dict)

    # Risks & Conflicts
    missing_clauses: List[str] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    risk_flags: List[Dict[str, Any]] = Field(default_factory=list)

    # Overall recommendation
    overall_status: str = Field(default="READY_FOR_REVIEW", description="READY_FOR_REVIEW | CHANGES_RECOMMENDED | CRITICAL_ISSUES_FOUND")
    confidence: float = Field(default=0.98, ge=0, le=1)
    contract_body: Optional[str] = Field(default="")

    # Normalized fields for DB schema compatibility
    creator_name: Optional[str] = None
    creator_username: Optional[str] = None
    campaign_name: Optional[str] = None
    agreed_value: float = Field(default=0.0, ge=0)
    currency: str = "INR"
    start_date: str = Field(default="")
    end_date: str = Field(default="")
    payment_due: str = Field(default="Net 7 post completion")
    risk_level: str = Field(default="LOW", description="LOW | MEDIUM | HIGH")
    deliverables: List[str] = Field(default_factory=list)
    additional_terms: Optional[str] = Field(default="")
    ai_risks: List[str] = Field(default_factory=list)

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
        if v is None:
            return 0.0
        try:
            return float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("agreed_value must be numeric") from exc

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        if v is None:
            return 0.98
        try:
            val = float(v)
        except (TypeError, ValueError) as exc:
            raise ValueError("confidence must be numeric") from exc
        if val > 1 and val <= 100:
            val = val / 100.0
        return max(0.0, min(1.0, val))


class ContractAgent(BaseAgent):
    name = AgentNames.CONTRACT
    version = "2.0.0"
    description = (
        "Synthesizes complete, binding influencer collaboration agreements from confirmed commercial terms with zero generic blanks."
    )

    def validate_input(self, ctx: AgentContext) -> None:
        super().validate_input(ctx)
        target_inf_id = ctx.extras.get("influencer_id")
        confirmed_terms = ctx.extras.get("confirmed_terms") or ctx.extras.get("agreed_terms") or {}

        if not target_inf_id and not confirmed_terms.get("influencer_id"):
            raise AgentValidationException(
                detail="CONTRACT_INFORMATION_REQUIRED: An influencer must be selected for contract generation."
            )

    async def build_context(self, ctx: AgentContext) -> Dict[str, Any]:
        campaign = ctx.campaign
        target_inf_id = ctx.extras.get("influencer_id")
        provided_terms = ctx.extras.get("confirmed_terms") or ctx.extras.get("agreed_terms") or {}
        contract_text = ctx.extras.get("contract_text")

        # 1. Run deterministic readiness service
        readiness_service = ContractReadinessService(ctx.db)
        readiness = await readiness_service.check_readiness(
            campaign_id=campaign.id,
            influencer_id=target_inf_id,
            user=ctx.user,
        )

        if not readiness.ready:
            if readiness.status == "NOT_APPLICABLE":
                raise AgentValidationException(
                    detail=f"CONTRACT_GATE: {readiness.blocking_reason or 'Contract is not applicable for this creator.'}"
                )
            if readiness.status == "LOCKED":
                raise AgentValidationException(
                    detail=f"CONTRACT_GATE: {readiness.blocking_reason or 'Creator must be ACCEPTED before contract generation.'}"
                )
            if readiness.status == "CONTRACT_INFORMATION_REQUIRED":
                raise AgentValidationException(
                    detail=f"CONTRACT_INFORMATION_REQUIRED: {readiness.blocking_reason or 'Required commercial terms missing.'}"
                )
            raise AgentValidationException(detail=f"CONTRACT_GATE: {readiness.blocking_reason}")

        # 2. Load CampaignInfluencer & Influencer
        stmt = (
            select(CampaignInfluencer)
            .options(selectinload(CampaignInfluencer.influencer))
            .where(
                CampaignInfluencer.campaign_id == campaign.id,
                CampaignInfluencer.influencer_id == target_inf_id,
            )
        )
        links_res = await ctx.db.execute(stmt)
        link = links_res.scalar_one_or_none()
        if not link or not link.influencer:
            raise AgentValidationException(detail="Creator details not found in database.")

        influencer = link.influencer

        # 3. Load latest OutreachMessage
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

        # 4. Merge and build structured confirmed terms payload
        suggested = dict(readiness.suggested_terms or {})
        
        # If provided_terms has flat or nested structure, merge properly
        merged_terms = dict(suggested)
        if isinstance(provided_terms, dict):
            for k, v in provided_terms.items():
                if isinstance(v, dict) and k in merged_terms and isinstance(merged_terms[k], dict):
                    merged_terms[k].update(v)
                elif v is not None:
                    merged_terms[k] = v

        # If flat agreed_rate or deliverables passed, ensure they are reflected
        if "agreed_rate" in provided_terms and provided_terms["agreed_rate"]:
            rate_val = float(provided_terms["agreed_rate"])
            merged_terms["compensation"]["total"] = rate_val
            merged_terms["payment"]["advance_amount"] = round(rate_val * 0.5, 2)
            merged_terms["payment"]["balance_amount"] = round(rate_val * 0.5, 2)

        if "deliverables" in provided_terms and provided_terms["deliverables"]:
            d_val = provided_terms["deliverables"]
            merged_terms["deliverables"] = d_val if isinstance(d_val, list) else [str(d_val)]

        # Validate with ContractTermsPayload
        try:
            payload_obj = ContractTermsPayload.model_validate(merged_terms)
            final_commercial_terms = payload_obj.model_dump()
        except Exception as exc:
            logger.warning("ContractTermsPayload fallback on validation error: %s", exc)
            final_commercial_terms = merged_terms

        return {
            "campaign": {
                "campaign_id": campaign.id,
                "name": campaign.name,
                "brand": campaign.brand,
                "objective": campaign.objective,
                "description": campaign.description or "Brand promotional campaign",
                "start_date": campaign.start_date or "Launch Date",
                "end_date": campaign.end_date or "Launch + 30",
            },
            "influencer": {
                "influencer_id": influencer.id,
                "name": influencer.name,
                "username": influencer.username,
                "platform": influencer.platform,
                "profile_url": influencer.profile_url or f"https://{influencer.platform}.com/{influencer.username}",
                "niches": influencer.niches or [],
            },
            "confirmed_terms": final_commercial_terms,
            "outreach": {
                "status": "ACCEPTED",
                "acceptance_confirmed": True,
                "outreach_id": last_outreach.id if last_outreach else None,
                "pitch": (last_outreach.body or last_outreach.short_dm) if last_outreach else "Standard pitch",
            },
            "contract_document_text": contract_text,
        }

    def build_system_prompt(self, ctx: AgentContext) -> str:
        return "\n".join(
            [
                "You are the Contract Agent of Auralytics.",
                "Your task is to generate a complete, professional, legally sound influencer collaboration agreement from CONTRACT TERMS ALREADY CONFIRMED by the user.",
                "The supplied contract data is authoritative and final.",
                "",
                "ABSOLUTE RULES:",
                "1. DO NOT invent or modify:",
                "   - parties",
                "   - compensation amounts or currency",
                "   - payment percentages, advance amount, balance amount, or payment method",
                "   - deliverables or quantities",
                "   - timelines and deadlines",
                "   - usage rights scope or duration",
                "   - ownership structure",
                "   - exclusivity rules",
                "   - revision rounds count",
                "   - content approval requirements",
                "   - product claim restrictions",
                "   - cancellation or termination terms",
                "",
                "2. NO GENERIC PLACEHOLDERS OR BLANKS:",
                "   The agreement MUST be completely written and usable.",
                "   Under NO circumstances should you output bracketed blanks or placeholders such as:",
                "   [Insert Creator Name], [Enter Amount], [Specify Payment Method], [Enter Usage Rights], [Add Timeline], [Enter Exclusivity Period], [Specify Number of Revisions], TBD, or Lorem Ipsum.",
                "   Every single clause must contain specific, concrete language derived from the confirmed terms.",
                "",
                "3. GENERATE FULL SECTIONS IN CONTRACT BODY:",
                "   Include well-drafted legal sections:",
                "   1. Agreement and Parties",
                "   2. Scope of Collaboration",
                "   3. Deliverables and Specifications",
                "   4. Compensation and Payment Structure (Include exact advance & balance numbers)",
                "   5. Payment Method and Timing",
                "   6. Content Submission and Approval Process",
                "   7. Revisions and Creative Scope",
                "   8. Campaign Timeline and Deadlines",
                "   9. Product Claims and Compliance",
                "   10. Usage Rights and Marketing License",
                "   11. Intellectual Property and Content Ownership",
                "   12. Exclusivity Obligations",
                "   13. Sponsorship Disclosure and Platform Compliance",
                "   14. Confidentiality",
                "   15. Cancellation and Advance Refund Policy",
                "   16. Termination for Cause",
                "   17. Additional Agreed Terms",
                "   18. Execution and Signatures",
                "",
                "4. Return structured JSON matching the ContractAgentOutput schema.",
                MISSING_DATA_RULE,
                SECURITY_RULE,
            ]
        )

    def build_user_prompt(self, ctx: AgentContext, context_payload: Dict[str, Any]) -> str:
        camp = context_payload["campaign"]
        inf = context_payload["influencer"]
        terms = context_payload["confirmed_terms"]
        doc_text = context_payload.get("contract_document_text")

        comp = terms.get("compensation") or {}
        pay = terms.get("payment") or {}
        time = terms.get("timeline") or {}
        rev = terms.get("revisions") or {}
        appr = terms.get("approval") or {}
        claims = terms.get("product_claims") or {}
        usage = terms.get("usage_rights") or {}
        owner = terms.get("ownership") or {}
        excl = terms.get("exclusivity") or {}
        canc = terms.get("cancellation") or {}
        term = terms.get("termination") or {}

        doc_section = (
            f"UPLOADED EXISTING CONTRACT TEXT TO VERIFY:\n```\n{doc_text}\n```"
            if doc_text
            else "NO EXISTING CONTRACT TEXT UPLOADED. Generate the full complete formal agreement document body incorporating every confirmed parameter."
        )

        return (
            f"GENERATE FORMAL INFLUENCER COLLABORATION AGREEMENT FOR:\n"
            f"Brand / Sponsor: {camp['brand']}\n"
            f"Campaign Name: {camp['name']} (Objective: {camp['objective']})\n"
            f"Influencer / Creator: {inf['name']} (@{inf['username']}) on {inf['platform']}\n\n"
            f"CONFIRMED COMMERCIAL & LEGAL TERMS:\n"
            f"1. Compensation: {comp.get('currency', 'INR')} {float(comp.get('total', 0)):,.2f}\n"
            f"2. Payment Structure: {pay.get('terms_text') or f'{pay.get('advance_percentage')}% Advance ({comp.get('currency')} {pay.get('advance_amount')}), {pay.get('balance_percentage')}% Balance ({comp.get('currency')} {pay.get('balance_amount')}) via {pay.get('method')} within {pay.get('balance_due_days')} days'}\n"
            f"3. Deliverables: {json.dumps(terms.get('deliverables', []))}\n"
            f"4. Timeline: Flight from {time.get('start_date')} to {time.get('end_date')}; Draft due {time.get('draft_submission_deadline')}; Publishing due {time.get('publishing_deadline')}\n"
            f"5. Revisions: Maximum {rev.get('allowed_rounds', 2)} rounds covering {rev.get('scope')}\n"
            f"6. Pre-Publication Approval: {'REQUIRED before posting' if appr.get('pre_publication_required', True) else 'Not required'}\n"
            f"7. Product Claims: {claims.get('claim_guidelines') or 'Only brand-approved claims permitted'}\n"
            f"8. Usage Rights: Organic Reposting: {'Yes' if usage.get('organic_reposting') else 'No'}, Paid Ads: {'Yes' if usage.get('paid_ads') else 'No'}, Duration: {usage.get('duration')}, Territory: {usage.get('territory')}\n"
            f"9. Ownership: {owner.get('license_grant') or 'Influencer retains copyright, Brand receives usage license'}\n"
            f"10. Exclusivity: {'Yes - ' + str(excl.get('category')) + ' for ' + str(excl.get('duration_days')) + ' days' if excl.get('required') else 'Non-exclusive'}\n"
            f"11. Cancellation: {canc.get('brand_cancellation')} | {canc.get('influencer_cancellation')}\n"
            f"12. Termination: {json.dumps(term.get('grounds', []))}\n"
            f"13. Additional Conditions: {terms.get('additional_terms') or 'Standard collaboration guidelines'}\n\n"
            f"{doc_section}\n\n"
            f"Synthesize the complete, professional contract_body text with ZERO generic blanks. Ensure all figures, names, and rights are explicitly written into the agreement."
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
            temperature=0.1,
            max_tokens=4000,
        )
        data = structured.model_dump()
        camp = context_payload.get("campaign") or {}
        inf = context_payload.get("influencer") or {}
        terms = context_payload.get("confirmed_terms") or {}
        comp = terms.get("compensation") or {}
        pay = terms.get("payment") or {}
        time_terms = terms.get("timeline") or {}
        usage_terms = terms.get("usage_rights") or {}
        excl_terms = terms.get("exclusivity") or {}

        # Commercial Term Protection: Authoritative user terms strictly overwrite / lock factual business data
        data["influencer_id"] = inf.get("influencer_id")
        data["creator_name"] = inf.get("name") or "Creator"
        data["creator_username"] = inf.get("username") or "creator"
        data["campaign_name"] = camp.get("name") or ctx.campaign.name
        data["agreed_value"] = float(comp.get("total") or terms.get("agreed_rate") or 0.0)
        data["currency"] = str(comp.get("currency") or terms.get("currency") or "INR")
        data["deliverables"] = list(terms.get("deliverables") or [])
        data["start_date"] = str(time_terms.get("start_date") or terms.get("timeline_start") or camp.get("start_date") or "")
        data["end_date"] = str(time_terms.get("end_date") or terms.get("timeline_end") or camp.get("end_date") or "")
        data["payment_due"] = str(pay.get("terms_text") or terms.get("payment_terms") or "Net 7 post completion")
        data["additional_terms"] = str(terms.get("additional_terms") or "")
        data["outreach_id"] = (context_payload.get("outreach") or {}).get("outreach_id")

        if not data.get("parties"):
            data["parties"] = {
                "brand": camp.get("brand") or "Brand",
                "influencer": data["creator_name"],
            }

        # Build clean fallback contract body if none synthesized
        if not data.get("contract_body") or len(data.get("contract_body", "").strip()) < 50:
            deliverables_text = "\n".join(f"  - {d}" for d in data["deliverables"])
            data["contract_body"] = (
                f"INFLUENCER COLLABORATION AGREEMENT\n\n"
                f"This Influencer Collaboration Agreement is entered into between {camp.get('brand')} ('Brand/Sponsor') "
                f"and {data['creator_name']} (@{data['creator_username']}) ('Creator/Influencer') regarding the '{data['campaign_name']}' campaign.\n\n"
                f"1. SCOPE & DELIVERABLES:\n{deliverables_text}\n\n"
                f"2. COMPENSATION & PAYMENT:\nTotal Fee: {data['currency']} {data['agreed_value']:,.2f}.\n{data['payment_due']}\n\n"
                f"3. CAMPAIGN TIMELINE:\nFlight Window: {data['start_date']} through {data['end_date']}.\n\n"
                f"4. USAGE RIGHTS & IP:\nUsage: {usage_terms.get('duration', '3 Months')} organic social media license. Creator retains copyright.\n\n"
                f"5. EXCLUSIVITY:\n{'Direct competitor exclusivity applies for ' + str(excl_terms.get('duration_days', 30)) + ' days.' if excl_terms.get('required') else 'Non-exclusive collaboration.'}\n\n"
                f"6. CONTENT APPROVAL & REVISIONS:\nBrand pre-publication approval required. Includes up to 2 revision rounds for factual accuracy.\n\n"
                f"7. SIGNATURES:\nBy executing below, the parties agree to all terms and conditions set forth herein."
            )

        # Sanitize any accidental placeholder brackets
        data["contract_body"] = re.sub(r"\[(Insert|Enter|Specify|Add)\s+[^\]]+\]", "", data["contract_body"], flags=re.IGNORECASE)

        summary = (
            f"Complete contract synthesized for {data['creator_name']} (@{data['creator_username']}) — "
            f"Fee: {data['currency']} {data['agreed_value']:,.2f} | Status: {data['overall_status']}"
        )

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
        terms = context_payload.get("confirmed_terms") or {}
        comp = terms.get("compensation") or {}

        expected_rate = float(comp.get("total") or terms.get("agreed_rate") or 0.0)
        if expected_rate <= 0:
            raise AgentValidationException(
                detail="Contract validation failed: final collaboration amount must be greater than 0"
            )

        data["agreed_value"] = expected_rate
        data["currency"] = str(comp.get("currency") or terms.get("currency") or "INR")
        data["deliverables"] = list(terms.get("deliverables") or [])
        data["start_date"] = str((terms.get("timeline") or {}).get("start_date") or terms.get("timeline_start") or "")
        data["end_date"] = str((terms.get("timeline") or {}).get("end_date") or terms.get("timeline_end") or "")

        result.data = data
        return result
