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
    "campaign_name": ("campaign_name", "campaign", "campaign title", "name"),
    "brand": ("brand", "company", "company_name"),
    "product": ("product", "sku"),
    "description": ("description", "brief", "campaign_description"),
    "objective": ("objective", "goal"),
    "platform": ("platform", "platforms"),
    "audience": ("audience", "target_audience"),
    "start_date": ("start_date", "start", "campaign_start"),
    "end_date": ("end_date", "end", "campaign_end"),
    "budget": ("budget", "planned_budget"),
    "actual_spend": ("actual_spend", "spend", "total_spend"),
    "status": ("status", "campaign_status", "lifecycle_status"),
    "creator_name": ("creator_name", "influencer_name", "creator", "influencer"),
    "handle": ("handle", "username", "channel"),
    "channel_id": ("channel_id", "youtube_id"),
    "channel_url": ("channel_url", "profile_url", "youtube_url"),
    "shortlisted": ("shortlisted", "shortlist"),
    "approved": ("approved", "creator_approved"),
    "discovered": ("discovered", "discovery"),
    "outreach_sent": ("outreach_sent", "email_sent", "outreach"),
    "outreach_date": ("outreach_date", "sent_at"),
    "message": ("message", "outreach_message", "email_body"),
    "creator_reply": ("creator_reply", "reply", "response"),
    "reply_date": ("reply_date", "responded_at"),
    "outreach_status": ("outreach_status", "negotiation_status"),
    "final_agreed_price": ("final_agreed_price", "agreed_price", "rate", "creator_rate"),
    "contract_status": ("contract_status",),
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
    "views": ("views", "view_count"),
    "likes": ("likes",),
    "comments": ("comments",),
    "engagement": ("engagement", "engagement_rate"),
    "revenue": ("revenue", "attributed_revenue"),
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
    buckets: Dict[str, HistoricalCampaignCandidate] = {}
    for table in tables:
        source_type = classify_source_type(table.filename)
        for row in table.rows:
            name = _stringify(_get(row, "campaign_name", ("campaign",)))
            if not name and row.get("unstructured_text"):
                name = _infer_name_from_text(str(row.get("unstructured_text")))
            if not name:
                name = _stringify(_get(row, "product")) or table.filename.rsplit(".", 1)[0]
            brand = _stringify(_get(row, "brand"))
            key = campaign_key(name, brand)
            cand = buckets.get(key)
            if cand is None:
                cand = HistoricalCampaignCandidate(key=key, campaign_name=name, brand=brand)
                buckets[key] = cand
            _apply_row(cand, row, table.filename, source_type)
    for cand in buckets.values():
        _finalize_candidate(cand)
    return list(buckets.values())


def _apply_row(cand: HistoricalCampaignCandidate, row: Dict[str, Any], filename: str, source_type: str) -> None:
    if filename not in cand.sources:
        cand.sources.append(filename)
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

    creator_name = _stringify(_get(row, "creator_name", ("influencer_name", "creator")))
    handle = _stringify(_get(row, "handle"))
    if creator_name or handle:
        existing = next((c for c in cand.creators if _same_creator(c, creator_name, handle)), None)
        if existing is None:
            existing = ExtractedCreator(name=creator_name, handle=handle)
            cand.creators.append(existing)
        existing.platform = existing.platform or _stringify(_get(row, "platform")) or "youtube"
        existing.channel_id = existing.channel_id or _stringify(_get(row, "channel_id"))
        existing.channel_url = existing.channel_url or _stringify(_get(row, "channel_url"))
        shortlisted = _as_bool(_get(row, "shortlisted"))
        if shortlisted is not None:
            existing.shortlisted = shortlisted
        approved = _as_bool(_get(row, "approved"))
        if approved is not None:
            existing.approved = approved
        discovered = _as_bool(_get(row, "discovered"))
        if discovered is True or existing.shortlisted or existing.approved:
            existing.discovered = True

    outreach_sent = _as_bool(_get(row, "outreach_sent"))
    message = _stringify(_get(row, "message"))
    reply = _stringify(_get(row, "creator_reply"))
    price = _as_float(_get(row, "final_agreed_price"))
    if outreach_sent or message or reply or price is not None or _get(row, "outreach_status"):
        cand.outreach_records.append(
            ExtractedOutreach(
                creator_name=creator_name,
                outreach_sent=outreach_sent if outreach_sent is not None else bool(message),
                outreach_date=_stringify(_get(row, "outreach_date")),
                message=message,
                creator_reply=reply,
                reply_date=_stringify(_get(row, "reply_date")),
                status=_stringify(_get(row, "outreach_status")),
                negotiation_status=_stringify(_get(row, "outreach_status")),
                final_agreed_price=price,
                currency=_stringify(_get(row, "currency")) or "INR",
                deliverables=_as_list(_get(row, "deliverables")),
            )
        )

    compensation = _as_float(_get(row, "compensation"))
    contract_status = _stringify(_get(row, "contract_status"))
    if compensation is not None or contract_status or source_type == "CONTRACT" and creator_name:
        _add_conflict(cand, creator_name or "campaign", "compensation", compensation, filename, source_type)
        cand.contracts.append(
            ExtractedContract(
                creator_name=creator_name,
                contract_status=contract_status,
                compensation=compensation,
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
    revenue = _as_float(_get(row, "revenue"))
    roas = _as_float(_get(row, "roas"))
    if views is not None or revenue is not None or roas is not None or _get(row, "measurement_date"):
        cand.performance_records.append(
            ExtractedPerformance(
                creator_name=creator_name,
                views=views,
                likes=_as_int(_get(row, "likes")),
                comments=_as_int(_get(row, "comments")),
                engagement=_as_float(_get(row, "engagement")),
                spend=_as_float(_get(row, "actual_spend")),
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
    evidence.discovery = any(c.discovered or c.name or c.handle for c in cand.creators) or bool(cand.creators)
    evidence.shortlist = any(c.shortlisted or c.approved for c in cand.creators)
    evidence.outreach = any(
        r.outreach_sent or r.message or r.creator_reply or r.final_agreed_price is not None for r in cand.outreach_records
    )
    evidence.negotiation = any(r.final_agreed_price is not None or r.negotiation_status for r in cand.outreach_records)
    evidence.contract = any(
        r.compensation is not None or (r.contract_status or "").lower() in {"signed", "approved", "completed", "done"}
        for r in cand.contracts
    )
    evidence.content = bool(cand.content_records)
    evidence.performance = bool(cand.performance_records)
    evidence.optimization = bool(cand.optimization_records)
    evidence.approval = any((a.status or "").lower() in {"approved", "complete", "completed"} for a in cand.approvals)
    evidence.strategy = bool(cand.objective or cand.description or cand.audience)
    cand.evidence = evidence
    cand.classification, cand.current_stage, cand.workflow_state, cand.next_step_key, warning = classify_lifecycle(evidence, cand.reported_status)
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
    _, tab = CampaignWorkflowService._step_target("preview", _ui_step(cand.next_step_key))
    cand.continue_tab = tab


def classify_lifecycle(
    evidence: StageEvidence,
    reported_status: Optional[str],
) -> Tuple[str, str, str, str, Optional[str]]:
    """Map extracted evidence onto existing WorkflowState values. Does not run agents."""
    reported = (reported_status or "").strip().lower()
    completed_words = reported in {"completed", "complete", "historical", "closed", "done"}

    if evidence.optimization and evidence.performance and evidence.contract and evidence.outreach:
        if evidence.approval or completed_words:
            return "COMPLETED", "COMPLETE", WorkflowState.COMPLETED, "", None
        return (
            "IN_PROGRESS",
            "APPROVAL",
            WorkflowState.OPTIMIZATION_APPROVAL_PENDING,
            "APPROVE_OPTIMIZATION",
            None,
        )
    if evidence.performance and evidence.contract:
        if completed_words and not evidence.optimization:
            return (
                "NEEDS_REVIEW",
                "OPTIMIZATION",
                WorkflowState.OPTIMIZATION_PENDING,
                "OPTIMIZE_CAMPAIGN",
                "A performance report exists but formal completion/approval was not confirmed.",
            )
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

    if completed_words and evidence.contract and evidence.performance:
        return "COMPLETED", "COMPLETE", WorkflowState.COMPLETED, "", None
    if completed_words:
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
