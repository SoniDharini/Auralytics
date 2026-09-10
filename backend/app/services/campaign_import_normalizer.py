"""Normalize parsed tables into HistoricalCampaignCandidate records."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.workflow_states import WorkflowState
from app.models.campaign import Campaign
from app.schemas.campaign_import import (
    DuplicateMatch,
    ExtractedApproval,
    ExtractedContent,
    ExtractedContract,
    ExtractedCreator,
    ExtractedOptimization,
    ExtractedOutreach,
    ExtractedPerformance,
    FieldConflict,
    HistoricalCampaignCandidate,
    HistoricalCampaignImportPreview,
    StageEvidence,
)
from app.services.campaign_workflow_service import CampaignWorkflowService
from app.services.document_parsers import ParsedTable, classify_source_type

_COL = {
    "campaign_id": ("campaign_id", "campaign id", "cmp_id", "id", "campaign identifier"),
    "campaign_name": ("campaign_name", "campaign name", "campaign", "campaign title", "name"),
    "brand": ("brand", "company", "company_name", "company name"),
    "product": ("product", "sku", "item"),
    "description": ("description", "brief", "campaign_description", "campaign description", "notes", "comments"),
    "objective": ("objective", "goal"),
    "platform": ("platform", "platforms"),
    "audience": ("audience", "target_audience", "target audience"),
    "start_date": ("start_date", "start date", "start", "campaign_start"),
    "end_date": ("end_date", "end date", "end", "campaign_end"),
    "budget": ("budget", "planned_budget", "planned budget"),
    "actual_spend": ("actual_spend", "amount_spent", "amount spent", "spend", "total_spend", "total spend"),
    "status": ("final_status", "final status", "status", "campaign_status", "campaign status", "lifecycle_status"),
    "campaign_stage": ("campaign_stage", "campaign stage", "stage", "lifecycle_stage"),
    "influencers_selected": ("influencers_selected", "influencers selected", "selected_count", "creators_selected"),
    "influencer_names": ("influencer_names", "influencer names", "influencers"),
    "creator_name": (
        "creator_name",
        "creator / channel name",
        "creator_channel_name",
        "channel_name",
        "channel name",
        "influencer_name",
        "influencer name",
        "creator name",
        "creator",
        "influencer",
    ),
    "handle": ("handle", "username", "channel"),
    "channel_id": ("channel_id", "youtube_id"),
    "channel_url": (
        "channel_url",
        "channel_link",
        "channel link",
        "profile_url",
        "profile link",
        "youtube_url",
        "channel url",
    ),
    "category": (
        "category",
        "category / niche",
        "category_niche",
        "niche",
        "genre",
    ),
    "followers": (
        "followers",
        "follower / subscriber count",
        "follower_subscriber_count",
        "subscriber count",
        "subscribers",
        "follower count",
    ),
    "audience_fit_score": ("audience_fit_score", "audience fit score", "fit_score", "fit score"),
    "match_score": ("match_score", "match score", "score"),
    "predicted_roas": ("predicted_roas", "predicted roas"),
    "discovery_decision": ("discovery_decision", "discovery decision", "decision", "discovery status"),
    "outreach_result": ("outreach_result", "outreach result"),
    "shortlisted": ("shortlisted", "shortlist", "selected"),
    "approved": ("approved", "creator_approved"),
    "discovered": ("discovered", "discovery"),
    "outreach_sent": ("outreach_sent", "email_sent", "outreach"),
    "outreach_date": ("outreach_date", "sent_at"),
    "message": ("message", "outreach_message", "email_body"),
    "creator_reply": ("creator_reply", "reply", "response"),
    "reply_date": ("reply_date", "responded_at"),
    "outreach_status": ("outreach_status", "outreach status", "negotiation_status"),
    "final_agreed_price": ("final_agreed_price", "agreed_price", "rate", "creator_rate"),
    "contract_status": ("contract_status", "contract status"),
    "compensation": ("compensation", "contract_value", "contract_amount"),
    "currency": ("currency",),
    "deliverables": ("deliverables", "deliverable"),
    "payment_terms": ("payment_terms",),
    "usage_rights": ("usage_rights",),
    "exclusivity": ("exclusivity",),
    "signed_date": ("signed_date", "contract_signed"),
    "content_url": ("content_url", "video_url", "youtube_url", "url"),
    "video_id": ("video_id",),
    "published_at": ("published_at", "publish_date"),
    "views": (
        "views",
        "views / reach",
        "views_reach",
        "view_count",
        "avg views",
        "avg_views",
        "total_reach",
        "total reach",
        "reach",
    ),
    "reach": (
        "reach",
        "views / reach",
        "views_reach",
        "total_reach",
        "total reach",
    ),
    "likes": ("likes",),
    "comments": ("comments",),
    "clicks": ("clicks",),
    "conversions": ("conversions",),
    "engagement": ("engagement", "engagement_rate", "engagement rate"),
    "revenue": ("revenue", "revenue_generated", "revenue generated", "attributed_revenue"),
    "roas": ("roas",),
    "roi": ("roi",),
    "measurement_date": ("measurement_date", "report_date", "as_of"),
    "optimization": ("optimization", "recommendations"),
}

_TRUE = {"true", "yes", "y", "1", "done", "completed", "complete", "sent", "✓", "checked"}
_MONEY_RE = re.compile(r"[₹$€,\s]")


def _norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _lookup(row: Dict[str, Any], *aliases: str) -> Any:
    mapped = {_norm_key(k): v for k, v in row.items()}
    for alias in aliases:
        key = _norm_key(alias)
        if key in mapped:
            return mapped[key]
    return None


def _get(row: Dict[str, Any], field: str, extra: Tuple[str, ...] = ()) -> Any:
    aliases = _COL.get(field, (field,)) + extra
    return _lookup(row, *aliases)


def _as_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in _TRUE:
        return True
    if text in {"false", "no", "n", "0", "pending", "missing", "not found"}:
        return False
    return None


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _MONEY_RE.sub("", str(value))
    try:
        return float(text)
    except ValueError:
        return None


def _as_int(value: Any) -> Optional[int]:
    number = _as_float(value)
    if number is None:
        return None
    return int(number)


def _as_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    parts = [p.strip() for p in re.split(r"[|,;]", str(value)) if p.strip()]
    return parts or None


def campaign_key(name: Optional[str], brand: Optional[str] = None) -> str:
    raw = f"{name or ''}::{brand or ''}"
    folded = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-") or "unnamed-campaign"


def merge_tables(tables: Iterable[ParsedTable]) -> List[HistoricalCampaignCandidate]:
    candidates: List[HistoricalCampaignCandidate] = []
    by_ext_id: Dict[str, HistoricalCampaignCandidate] = {}
    by_key: Dict[str, HistoricalCampaignCandidate] = {}

    for table in tables:
        source_type = classify_source_type(table.filename)
        for row in table.rows:
            raw_id = _stringify(_get(row, "campaign_id"))
            name = _stringify(_get(row, "campaign_name", ("campaign",)))
            if not name and row.get("unstructured_text"):
                name = _infer_name_from_text(str(row.get("unstructured_text")))
            brand = _stringify(_get(row, "brand"))

            ext_id = _norm_key(raw_id) if raw_id else None
            key = campaign_key(name, brand) if name else None

            cand: Optional[HistoricalCampaignCandidate] = None
            if ext_id and ext_id in by_ext_id:
                cand = by_ext_id[ext_id]
            elif key and key in by_key:
                cand = by_key[key]

            if cand is None:
                if not name and not ext_id:
                    name = _stringify(_get(row, "product")) or table.filename.rsplit(".", 1)[0]
                    key = campaign_key(name, brand)
                    if key in by_key:
                        cand = by_key[key]

            if cand is None:
                cand_key = key or (f"id-{ext_id}" if ext_id else campaign_key(name or "unnamed", brand))
                cand = HistoricalCampaignCandidate(
                    key=cand_key,
                    external_id=raw_id,
                    campaign_name=name,
                    brand=brand,
                )
                candidates.append(cand)
                if ext_id:
                    by_ext_id[ext_id] = cand
                if key:
                    by_key[key] = cand
            else:
                if raw_id and not cand.external_id:
                    cand.external_id = raw_id
                if ext_id and ext_id not in by_ext_id:
                    by_ext_id[ext_id] = cand
                if name and not cand.campaign_name:
                    cand.campaign_name = name
                    if not cand.brand and brand:
                        cand.brand = brand
                    cand.key = campaign_key(name, cand.brand)
                    by_key[cand.key] = cand
                if key and key not in by_key:
                    by_key[key] = cand

            _apply_row(cand, row, table.filename, source_type)

    for cand in candidates:
        _finalize_candidate(cand)
    return candidates


def _apply_row(cand: HistoricalCampaignCandidate, row: Dict[str, Any], filename: str, source_type: str) -> None:
    if filename not in cand.sources:
        cand.sources.append(filename)
    cand.external_id = cand.external_id or _stringify(_get(row, "campaign_id"))
    cand.brand = cand.brand or _stringify(_get(row, "brand"))
    cand.product = cand.product or _stringify(_get(row, "product"))
    cand.description = cand.description or _stringify(_get(row, "description"))
    cand.objective = cand.objective or _stringify(_get(row, "objective"))
    cand.platform = cand.platform or _stringify(_get(row, "platform"))
    cand.audience = cand.audience or _stringify(_get(row, "audience"))
    cand.start_date = cand.start_date or _stringify(_get(row, "start_date"))
    cand.end_date = cand.end_date or _stringify(_get(row, "end_date"))
    cand.budget = cand.budget if cand.budget is not None else _as_float(_get(row, "budget"))
    cand.actual_spend = cand.actual_spend if cand.actual_spend is not None else _as_float(_get(row, "actual_spend"))
    cand.reported_status = cand.reported_status or _stringify(_get(row, "status"))
    cand.reported_stage = cand.reported_stage or _stringify(_get(row, "campaign_stage"))
    sel_cnt = _as_int(_get(row, "influencers_selected"))
    if sel_cnt is not None:
        cand.selected_count = sel_cnt

    creator_name = _stringify(_get(row, "creator_name", ("influencer_name", "creator", "influencer")))
    handle = _stringify(_get(row, "handle"))
    if creator_name or handle:
        existing = next((c for c in cand.creators if _same_creator(c, creator_name, handle)), None)
        if existing is None:
            existing = ExtractedCreator(name=creator_name, handle=handle)
            cand.creators.append(existing)
        existing.platform = existing.platform or _stringify(_get(row, "platform")) or "youtube"
        existing.category = existing.category or _stringify(_get(row, "category"))
        existing.followers = existing.followers or _as_int(_get(row, "followers"))
        existing.engagement_rate = existing.engagement_rate or _as_float(_get(row, "engagement"))
        existing.audience_fit_score = existing.audience_fit_score or _as_float(_get(row, "audience_fit_score"))
        existing.match_score = existing.match_score or _as_float(_get(row, "match_score"))
        existing.predicted_roas = existing.predicted_roas or _as_float(_get(row, "predicted_roas"))
        existing.channel_id = existing.channel_id or _stringify(_get(row, "channel_id"))
        existing.channel_url = existing.channel_url or _stringify(_get(row, "channel_url"))

        decision = _stringify(_get(row, "discovery_decision"))
        if decision:
            existing.discovery_decision = decision
            if decision.lower() in ("selected", "shortlisted"):
                existing.shortlisted = True
            elif decision.lower() in ("rejected", "declined"):
                existing.shortlisted = False

        shortlisted = _as_bool(_get(row, "shortlisted"))
        if shortlisted is not None:
            existing.shortlisted = shortlisted
        approved = _as_bool(_get(row, "approved"))
        if approved is not None:
            existing.approved = approved

        outreach_res = _stringify(_get(row, "outreach_result"))
        if outreach_res:
            existing.outreach_result = outreach_res

        discovered = _as_bool(_get(row, "discovered"))
        if discovered is True or existing.shortlisted or existing.approved or existing.discovery_decision:
            existing.discovered = True

    names_raw = _get(row, "influencer_names")
    if names_raw:
        for name in _as_list(names_raw) or []:
            if not any(_same_creator(c, name, None) for c in cand.creators):
                cand.creators.append(ExtractedCreator(name=name, discovered=True))

    outreach_sent = _as_bool(_get(row, "outreach_sent"))
    message = _stringify(_get(row, "message"))
    reply = _stringify(_get(row, "creator_reply"))
    price = _as_float(_get(row, "final_agreed_price"))
    outreach_st = _stringify(_get(row, "outreach_status"))
    outreach_res = _stringify(_get(row, "outreach_result"))
    effective_outreach_status = outreach_res or outreach_st
    is_not_contacted = bool(
        effective_outreach_status
        and effective_outreach_status.lower() in (
            "not contacted",
            "not sent",
            "not started",
            "uncontacted",
            "none",
            "no",
            "n/a",
            "not_contacted",
        )
    )
    has_real_outreach_status = bool(effective_outreach_status and not is_not_contacted)

    if (
        outreach_sent
        or message
        or reply
        or price is not None
        or has_real_outreach_status
    ):
        cand.outreach_records.append(
            ExtractedOutreach(
                creator_name=creator_name,
                outreach_sent=outreach_sent if outreach_sent is not None else (
                    bool(message)
                    or (effective_outreach_status and effective_outreach_status.lower() in ("completed", "done", "sent", "accepted", "replied"))
                ),
                outreach_date=_stringify(_get(row, "outreach_date")),
                message=message,
                creator_reply=reply,
                reply_date=_stringify(_get(row, "reply_date")),
                status=effective_outreach_status,
                negotiation_status=effective_outreach_status,
                final_agreed_price=price,
                currency=_stringify(_get(row, "currency")) or "INR",
                deliverables=_as_list(_get(row, "deliverables")),
            )
        )

    compensation = _as_float(_get(row, "compensation"))
    contract_status = _stringify(_get(row, "contract_status"))
    if compensation is not None or contract_status or (source_type == "CONTRACT" and creator_name):
        _add_conflict(cand, creator_name or "campaign", "compensation", compensation, filename, source_type)
        cand.contracts.append(
            ExtractedContract(
                creator_name=creator_name,
                contract_status=contract_status,
                compensation=compensation if compensation is not None else (cand.actual_spend or cand.budget),
                currency=_stringify(_get(row, "currency")) or "INR",
                deliverables=_as_list(_get(row, "deliverables")),
                payment_terms=_stringify(_get(row, "payment_terms")),
                usage_rights=_stringify(_get(row, "usage_rights")),
                exclusivity=_stringify(_get(row, "exclusivity")),
                signed_date=_stringify(_get(row, "signed_date")),
                start_date=_stringify(_get(row, "start_date")),
                end_date=_stringify(_get(row, "end_date")),
            )
        )

    content_url = _stringify(_get(row, "content_url"))
    video_id = _stringify(_get(row, "video_id"))
    if content_url or video_id:
        cand.content_records.append(
            ExtractedContent(
                creator_name=creator_name,
                platform=_stringify(_get(row, "platform")) or "youtube",
                content_url=content_url,
                video_id=video_id,
                published_at=_stringify(_get(row, "published_at")),
            )
        )

    views = _as_int(_get(row, "views"))
    reach = _as_int(_get(row, "reach"))
    revenue = _as_float(_get(row, "revenue"))
    roas = _as_float(_get(row, "roas"))
    spend = _as_float(_get(row, "actual_spend"))
    engagement = _as_float(_get(row, "engagement"))
    clicks = _as_int(_get(row, "clicks"))
    conversions = _as_int(_get(row, "conversions"))
    if (
        views is not None
        or reach is not None
        or revenue is not None
        or roas is not None
        or spend is not None
        or clicks is not None
        or conversions is not None
        or _get(row, "measurement_date")
    ):
        cand.performance_records.append(
            ExtractedPerformance(
                creator_name=creator_name,
                views=views or reach,
                reach=reach,
                likes=_as_int(_get(row, "likes")),
                comments=_as_int(_get(row, "comments")),
                clicks=clicks,
                conversions=conversions,
                engagement=engagement,
                spend=spend,
                revenue=revenue,
                roas=roas,
                roi=_as_float(_get(row, "roi")),
                measurement_date=_stringify(_get(row, "measurement_date")),
            )
        )

    recs = _as_list(_get(row, "optimization"))
    if recs:
        cand.optimization_records.append(ExtractedOptimization(recommendations=recs, status=_stringify(_get(row, "status"))))

    approval_status = _stringify(_lookup(row, "approval_status", "approval"))
    if approval_status:
        cand.approvals.append(ExtractedApproval(status=approval_status))


def _add_conflict(
    cand: HistoricalCampaignCandidate,
    entity: str,
    field: str,
    value: Any,
    filename: str,
    source_type: str,
) -> None:
    if value is None:
        return
    existing = next((c for c in cand.conflicts if c.entity == entity and c.field == field), None)
    entry = {"value": value, "source_filename": filename, "source_type": source_type}
    if existing is None:
        cand.conflicts.append(FieldConflict(entity=entity, field=field, values=[entry]))
        return
    seen = {str(v.get("value")) for v in existing.values}
    if str(value) not in seen:
        existing.values.append(entry)


def _finalize_candidate(cand: HistoricalCampaignCandidate) -> None:
    cand.conflicts = [c for c in cand.conflicts if len({str(v.get("value")) for v in c.values}) > 1]
    evidence = StageEvidence(campaign=bool(cand.campaign_name))
    evidence.discovery = (
        any(c.discovered or c.name or c.handle for c in cand.creators)
        or bool(cand.creators)
        or bool(cand.reported_stage and "discovery" in cand.reported_stage.lower())
    )
    if cand.selected_count is not None and cand.selected_count == 0:
        evidence.shortlist = False
    elif cand.selected_count is not None and cand.selected_count > 0:
        evidence.shortlist = True
    else:
        evidence.shortlist = any(
            c.shortlisted is True
            or c.approved is True
            or (c.discovery_decision and c.discovery_decision.lower() in ("selected", "shortlisted"))
            for c in cand.creators
        )

    evidence.outreach = any(
        r.outreach_sent
        or r.message
        or r.creator_reply
        or r.final_agreed_price is not None
        or (r.status and r.status.lower() in ("completed", "accepted", "sent", "done"))
        for r in cand.outreach_records
    )
    evidence.negotiation = any(
        r.final_agreed_price is not None
        or (r.status and r.status.lower() in ("accepted", "negotiating", "replied"))
        for r in cand.outreach_records
    )
    evidence.contract = any(
        r.compensation is not None
        or (r.contract_status or "").lower() in {"signed", "approved", "completed", "done"}
        for r in cand.contracts
    )
    evidence.content = bool(cand.content_records)
    evidence.performance = bool(cand.performance_records) or bool(
        cand.actual_spend is not None and (cand.reported_status or "").lower() in ("completed", "complete", "closed")
    )
    evidence.optimization = bool(cand.optimization_records)
    evidence.approval = any((a.status or "").lower() in {"approved", "complete", "completed"} for a in cand.approvals)
    has_pending_approval = any((a.status or "").lower() in {"pending", "waiting"} for a in cand.approvals)
    evidence.strategy = bool(cand.objective or cand.description or cand.audience or cand.product)
    cand.evidence = evidence
    cand.classification, cand.current_stage, cand.workflow_state, cand.next_step_key, warning = classify_lifecycle(
        evidence,
        cand.reported_status,
        reported_stage=cand.reported_stage,
        has_pending_approval=has_pending_approval,
    )
    if warning:
        cand.warnings.append(warning)
    if cand.conflicts:
        cand.classification = "NEEDS_REVIEW"
        cand.warnings.append("Conflicting values need review before import.")
    if not cand.campaign_name:
        cand.classification = "NEEDS_REVIEW"
        cand.warnings.append("Campaign name was not found.")
    filled = sum(1 for flag in evidence.model_dump().values() if flag)
    cand.confidence = round(min(0.99, 0.35 + filled * 0.07), 2)
    if cand.classification == "COMPLETED":
        cand.continue_route = None
        cand.continue_tab = "overview"
        cand.next_step_key = ""
        cand.current_stage = "COMPLETE"
    else:
        _, tab = CampaignWorkflowService._step_target("preview", _ui_step(cand.next_step_key))
        cand.continue_tab = tab


def classify_lifecycle(
    evidence: StageEvidence,
    reported_status: Optional[str],
    reported_stage: Optional[str] = None,
    has_pending_approval: bool = False,
) -> Tuple[str, str, str, str, Optional[str]]:
    """Map extracted evidence onto existing WorkflowState values. Does not run agents."""
    reported = (reported_status or "").strip().lower()
    completed_words = reported in {"completed", "complete", "historical", "closed", "done"}
    stage_completed = bool(
        reported_stage and any(w in reported_stage.lower() for w in ("completed", "complete", "closed"))
    )

    if (completed_words or stage_completed) and evidence.contract and evidence.performance and evidence.outreach:
        return "COMPLETED", "COMPLETE", WorkflowState.COMPLETED, "", None

    if evidence.optimization and evidence.performance and evidence.contract and evidence.outreach:
        if completed_words or stage_completed:
            return "COMPLETED", "COMPLETE", WorkflowState.COMPLETED, "", None
        return (
            "IN_PROGRESS",
            "APPROVAL",
            WorkflowState.OPTIMIZATION_APPROVAL_PENDING,
            "APPROVE_OPTIMIZATION",
            None,
        )

    if evidence.performance and evidence.contract:
        return "IN_PROGRESS", "OPTIMIZATION", WorkflowState.OPTIMIZATION_PENDING, "OPTIMIZE_CAMPAIGN", None

    if evidence.contract and not evidence.performance:
        if evidence.content:
            return "IN_PROGRESS", "PERFORMANCE", WorkflowState.PERFORMANCE_MONITORING, "ANALYZE_PERFORMANCE", None
        return "IN_PROGRESS", "PERFORMANCE", WorkflowState.CAMPAIGN_LIVE, "TRACK_PERFORMANCE", None

    if evidence.outreach and not evidence.contract:
        return "IN_PROGRESS", "CONTRACT", WorkflowState.CONTRACT_PENDING, "CONTRACT", None

    if evidence.shortlist and not evidence.outreach:
        return "IN_PROGRESS", "OUTREACH", WorkflowState.OUTREACH_PENDING, "GENERATE_OUTREACH", None

    if evidence.discovery and not evidence.shortlist:
        return "IN_PROGRESS", "SHORTLIST", WorkflowState.DISCOVERY_COMPLETED, "SHORTLIST_INFLUENCERS", None

    if evidence.campaign and not evidence.discovery:
        return "IN_PROGRESS", "DISCOVERY", WorkflowState.STRATEGY_COMPLETED, "DISCOVER_INFLUENCERS", None

    if completed_words or stage_completed:
        return (
            "NEEDS_REVIEW",
            "REVIEW",
            WorkflowState.CAMPAIGN_CREATED,
            "GENERATE_STRATEGY",
            "The file marked this campaign complete, but supporting stage evidence is incomplete.",
        )

    return "NEEDS_REVIEW", "REVIEW", WorkflowState.CAMPAIGN_CREATED, "GENERATE_STRATEGY", "Not enough evidence to classify this campaign."



def _ui_step(next_step_key: Optional[str]) -> str:
    mapping = {
        "GENERATE_STRATEGY": "STRATEGY",
        "DISCOVER_INFLUENCERS": "DISCOVERY",
        "SHORTLIST_INFLUENCERS": "SHORTLIST",
        "APPROVE_SHORTLIST": "APPROVAL",
        "GENERATE_OUTREACH": "OUTREACH",
        "REVIEW_OUTREACH": "OUTREACH",
        "CONTRACT": "CONTRACT",
        "TRACK_PERFORMANCE": "PERFORMANCE",
        "ANALYZE_PERFORMANCE": "PERFORMANCE",
        "OPTIMIZE_CAMPAIGN": "OPTIMIZATION",
        "REVIEW_OPTIMIZATION": "OPTIMIZATION",
        "APPROVE_OPTIMIZATION": "OPTIMIZATION",
    }
    return mapping.get(next_step_key or "", "CAMPAIGN_CREATED")


async def attach_duplicates(
    db: AsyncSession,
    owner_id: Any,
    campaigns: List[HistoricalCampaignCandidate],
) -> None:
    result = await db.execute(select(Campaign).where(Campaign.owner_id == owner_id))
    existing = list(result.scalars().all())
    for cand in campaigns:
        match = _find_duplicate(cand, existing)
        if match:
            cand.duplicate = match
            cand.warnings.append(f"This campaign may already exist as '{match.campaign_name}'.")


def _find_duplicate(cand: HistoricalCampaignCandidate, existing: List[Campaign]) -> Optional[DuplicateMatch]:
    target = campaign_key(cand.campaign_name, cand.brand)
    for camp in existing:
        key = campaign_key(camp.name, camp.brand)
        if key == target:
            return DuplicateMatch(campaign_id=camp.id, campaign_name=camp.name, confidence="HIGH", reason="Same name and brand")
        if _norm_key(camp.name) == _norm_key(cand.campaign_name or "") and cand.campaign_name:
            return DuplicateMatch(campaign_id=camp.id, campaign_name=camp.name, confidence="MEDIUM", reason="Similar campaign name")
    return None


def build_preview(
    import_id: str,
    status: str,
    campaigns: List[HistoricalCampaignCandidate],
    files: List[Dict[str, Any]],
    extra_warnings: Optional[List[str]] = None,
) -> HistoricalCampaignImportPreview:
    for cand in campaigns:
        if cand.classification == "COMPLETED":
            cand.continue_route = None
        elif cand.current_stage:
            cand.continue_tab = cand.continue_tab or "overview"
    warnings = list(extra_warnings or [])
    return HistoricalCampaignImportPreview(
        import_id=import_id,
        status=status,
        detected_campaigns=len(campaigns),
        completed_campaigns=sum(1 for c in campaigns if c.classification == "COMPLETED"),
        in_progress_campaigns=sum(1 for c in campaigns if c.classification == "IN_PROGRESS"),
        needs_review=sum(1 for c in campaigns if c.classification == "NEEDS_REVIEW"),
        creator_count=sum(len(c.creators) for c in campaigns),
        warnings=warnings,
        campaigns=campaigns,
        files=files,
    )


def _same_creator(creator: ExtractedCreator, name: Optional[str], handle: Optional[str]) -> bool:
    if handle and creator.handle and _norm_key(handle) == _norm_key(creator.handle):
        return True
    if name and creator.name and _norm_key(name) == _norm_key(creator.name):
        return True
    return False


def _stringify(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _infer_name_from_text(text: str) -> Optional[str]:
    match = re.search(r"campaign(?:\s*name)?\s*:\s*(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).splitlines()[0].strip()[:255]
    return None
