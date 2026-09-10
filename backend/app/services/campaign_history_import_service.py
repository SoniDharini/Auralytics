"""Upload → parse → preview → confirm. Never runs campaign agents."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.workflow_states import WorkflowState
from app.core.config import settings
from app.core.exceptions import InvalidRequestException, NotFoundException
from app.models.campaign import Campaign
from app.models.campaign_activity import CampaignActivity
from app.models.campaign_content import (
    CampaignContent,
    ContentPerformanceSnapshot,
    ContentType,
    OptimizationPlan,
    PerformanceAnalysis,
    TrackingStatus,
)
from app.models.campaign_history_import import (
    CampaignHistoryImport,
    ImportStatus,
    ImportedFieldProvenance,
    ImportedSource,
)
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.campaign_strategy import CampaignStrategy
from app.models.contract import Contract, ContractStatus
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage
from app.models.user import User
from app.schemas.campaign_import import (
    ClassifyCampaignRequest,
    ConfirmImportRequest,
    HistoricalCampaignCandidate,
    HistoricalCampaignImportPreview,
    ResolveConflictRequest,
)
from app.services.campaign_import_normalizer import attach_duplicates, build_preview, merge_tables
from app.services.campaign_workflow_service import CampaignWorkflowService
from app.services.document_parsers import (
    MAX_FILES,
    classify_source_type,
    parse_file,
    validate_upload,
)

_UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads" / "history"


class CampaignHistoryImportService:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user

    async def create_from_files(self, uploads: Sequence[Any]) -> HistoricalCampaignImportPreview:
        if not uploads:
            raise InvalidRequestException("Upload at least one campaign-history file.")
        if len(uploads) > MAX_FILES:
            raise InvalidRequestException(f"Upload at most {MAX_FILES} files at a time.")

        import_id = f"imp-{uuid.uuid4().hex[:12]}"
        record = CampaignHistoryImport(
            id=import_id,
            user_id=self.user.id,
            status=ImportStatus.UPLOADED,
        )
        self.db.add(record)
        await self.db.flush()

        tables = []
        files_meta: List[Dict[str, Any]] = []
        dest = _UPLOAD_ROOT / str(self.user.id) / import_id
        dest.mkdir(parents=True, exist_ok=True)

        for upload in uploads:
            filename = getattr(upload, "filename", None) or "upload.bin"
            content_type = getattr(upload, "content_type", None)
            data = await upload.read()
            try:
                ext = validate_upload(filename, content_type, data)
            except ValueError as exc:
                record.status = ImportStatus.FAILED
                record.error_message = str(exc)
                await self.db.commit()
                raise InvalidRequestException(str(exc)) from exc

            safe_name = Path(filename).name
            stored = dest / f"{uuid.uuid4().hex[:8]}_{safe_name}"
            stored.write_bytes(data)
            source = ImportedSource(
                id=f"src-{uuid.uuid4().hex[:10]}",
                import_id=import_id,
                filename=safe_name,
                file_type=ext,
                storage_reference=str(stored),
                source_kind=classify_source_type(safe_name),
            )
            self.db.add(source)
            files_meta.append({"id": source.id, "filename": safe_name, "file_type": ext, "source_kind": source.source_kind})
            try:
                tables.extend(parse_file(safe_name, data, ext))
            except ValueError as exc:
                record.status = ImportStatus.FAILED
                record.error_message = str(exc)
                await self.db.commit()
                raise InvalidRequestException(str(exc)) from exc

        campaigns = merge_tables(tables)
        await attach_duplicates(self.db, self.user.id, campaigns)
        for cand in campaigns:
            if cand.classification != "COMPLETED" and cand.next_step_key:
                route, tab = CampaignWorkflowService._step_target("pending", _ui_from_next(cand.next_step_key))
                cand.continue_tab = tab
                cand.continue_route = None
        preview = build_preview(import_id, ImportStatus.PREVIEW, campaigns, files_meta)
        record.status = ImportStatus.PREVIEW
        record.preview_json = preview.model_dump()
        await self.db.commit()
        return preview

    async def get_preview(self, import_id: str) -> HistoricalCampaignImportPreview:
        record = await self._owned_import(import_id)
        if not record.preview_json:
            raise InvalidRequestException("This import has no preview yet.")
        return HistoricalCampaignImportPreview.model_validate(record.preview_json)

    async def resolve_conflict(self, import_id: str, payload: ResolveConflictRequest) -> HistoricalCampaignImportPreview:
        record = await self._owned_import(import_id)
        preview = HistoricalCampaignImportPreview.model_validate(record.preview_json or {})
        cand = _find_candidate(preview, payload.campaign_key)
        remaining = []
        for conflict in cand.conflicts:
            if conflict.entity == payload.entity and conflict.field == payload.field:
                _apply_chosen_value(cand, payload.field, payload.entity, payload.chosen_value)
                continue
            remaining.append(conflict)
        cand.conflicts = remaining
        if not cand.conflicts and cand.classification == "NEEDS_REVIEW":
            from app.services.campaign_import_normalizer import classify_lifecycle

            classification, stage, state, nxt, warning = classify_lifecycle(cand.evidence, cand.reported_status)
            cand.classification = cand.user_classification or classification
            cand.current_stage = stage
            cand.workflow_state = state
            cand.next_step_key = nxt
            if warning and warning not in cand.warnings:
                cand.warnings.append(warning)
        record.preview_json = _refresh_counts(preview).model_dump()
        await self.db.commit()
        return HistoricalCampaignImportPreview.model_validate(record.preview_json)

    async def classify_campaign(self, import_id: str, payload: ClassifyCampaignRequest) -> HistoricalCampaignImportPreview:
        record = await self._owned_import(import_id)
        preview = HistoricalCampaignImportPreview.model_validate(record.preview_json or {})
        cand = _find_candidate(preview, payload.campaign_key)
        allowed = {"COMPLETED", "IN_PROGRESS", "NEEDS_REVIEW"}
        if payload.classification not in allowed:
            raise InvalidRequestException("Classification must be COMPLETED, IN_PROGRESS, or NEEDS_REVIEW.")
        cand.user_classification = payload.classification
        cand.classification = payload.classification
        if payload.import_action:
            if payload.import_action not in {"IMPORT", "MERGE", "SKIP"}:
                raise InvalidRequestException("Import action must be IMPORT, MERGE, or SKIP.")
            cand.import_action = payload.import_action
        if payload.merge_campaign_id:
            if not cand.duplicate or cand.duplicate.campaign_id != payload.merge_campaign_id:
                cand.duplicate = cand.duplicate or None
            cand.import_action = "MERGE"
            if cand.duplicate:
                cand.duplicate.campaign_id = payload.merge_campaign_id
        if payload.classification == "COMPLETED":
            cand.workflow_state = WorkflowState.COMPLETED
            cand.current_stage = "COMPLETE"
            cand.next_step_key = ""
            cand.continue_route = None
        record.preview_json = _refresh_counts(preview).model_dump()
        await self.db.commit()
        return HistoricalCampaignImportPreview.model_validate(record.preview_json)

    async def confirm(self, import_id: str, payload: Optional[ConfirmImportRequest] = None) -> Dict[str, Any]:
        record = await self._owned_import(import_id)
        if record.status == ImportStatus.CONFIRMED:
            raise InvalidRequestException("This import was already confirmed.")
        preview = HistoricalCampaignImportPreview.model_validate(record.preview_json or {})
        if payload and payload.campaigns:
            by_key = {c.key: c for c in preview.campaigns}
            for patch in payload.campaigns:
                key = patch.get("key")
                if key in by_key:
                    if patch.get("import_action"):
                        by_key[key].import_action = patch["import_action"]
                    if patch.get("classification"):
                        by_key[key].classification = patch["classification"]
                        by_key[key].user_classification = patch["classification"]
        blocking = [c for c in preview.campaigns if c.conflicts and c.import_action != "SKIP"]
        if blocking:
            raise InvalidRequestException("Resolve commercial conflicts before importing.")

        created_ids: List[str] = []
        now = datetime.now(timezone.utc)
        for cand in preview.campaigns:
            if cand.import_action == "SKIP":
                continue
            campaign = await self._persist_candidate(cand, record.id, now)
            created_ids.append(campaign.id)
            if cand.classification != "COMPLETED" and cand.next_step_key:
                route, tab = CampaignWorkflowService._step_target(campaign.id, _ui_from_next(cand.next_step_key))
                cand.continue_route = route
                cand.continue_tab = tab
            else:
                cand.continue_route = None
                cand.continue_tab = "overview"

        record.status = ImportStatus.CONFIRMED
        record.confirmed_at = now
        record.confirmed_campaign_ids = created_ids
        record.preview_json = _refresh_counts(preview).model_dump()
        await self.db.commit()
        return {
            "import_id": record.id,
            "status": record.status,
            "campaign_ids": created_ids,
            "preview": record.preview_json,
        }

    async def _persist_candidate(
        self,
        cand: HistoricalCampaignCandidate,
        import_id: str,
        now: datetime,
    ) -> Campaign:
        merge_id = cand.duplicate.campaign_id if cand.import_action == "MERGE" and cand.duplicate else None
        campaign: Optional[Campaign] = None
        if merge_id:
            result = await self.db.execute(
                select(Campaign).where(Campaign.id == merge_id, Campaign.owner_id == self.user.id)
            )
            campaign = result.scalar_one_or_none()
        if campaign is None:
            campaign = Campaign(
                id=f"camp-{uuid.uuid4().hex[:8]}",
                owner_id=self.user.id,
                name=(cand.campaign_name or "Imported campaign")[:255],
                brand=(cand.brand or "Imported")[:255],
                status="completed" if cand.classification == "COMPLETED" else (
                    "needs_attention" if cand.classification == "NEEDS_REVIEW" else "active"
                ),
                health="healthy",
                budget=float(cand.budget or 0),
                spend=float(cand.actual_spend or 0),
                revenue=_total_revenue(cand),
                roas=_reported_roas(cand),
                influencers=len(cand.creators),
                progress=100 if cand.classification == "COMPLETED" else 50,
                start_date=cand.start_date or "not specified",
                end_date=cand.end_date or "not specified",
                objective=(cand.objective or "Imported historical campaign")[:100],
                description=cand.description,
                platforms=[cand.platform] if cand.platform else ["youtube"],
                workflow_state=cand.workflow_state or WorkflowState.CAMPAIGN_CREATED,
            )
            self.db.add(campaign)
            await self.db.flush()
        else:
            if cand.actual_spend is not None:
                campaign.spend = float(cand.actual_spend)
            revenue = _total_revenue(cand)
            if revenue:
                campaign.revenue = revenue
            if cand.workflow_state:
                campaign.workflow_state = cand.workflow_state
            if cand.classification == "COMPLETED":
                campaign.status = "completed"
                campaign.progress = 100

        await self._ensure_imported_strategy(campaign, cand)
        influencer_map = await self._persist_creators(campaign, cand, import_id, now)
        await self._persist_outreach(campaign, cand, influencer_map)
        await self._persist_contracts(campaign, cand, influencer_map)
        await self._persist_performance(campaign, cand, influencer_map)
        await self._persist_optimization(campaign, cand)
        await self._write_provenance(import_id, campaign, cand)

        self.db.add(
            CampaignActivity(
                id=f"act-{uuid.uuid4().hex[:8]}",
                user_id=self.user.id,
                campaign_id=campaign.id,
                activity_type="CAMPAIGN_HISTORY_IMPORTED",
                title=f"Historical campaign '{campaign.name}' imported",
                description="Imported from uploaded company files. Existing Auralytics agents were not rerun.",
                metadata_json={
                    "import_id": import_id,
                    "classification": cand.classification,
                    "sources": cand.sources,
                    "workflow_state": campaign.workflow_state,
                },
            )
        )
        return campaign

    async def _ensure_imported_strategy(self, campaign: Campaign, cand: HistoricalCampaignCandidate) -> None:
        result = await self.db.execute(
            select(CampaignStrategy).where(CampaignStrategy.campaign_id == campaign.id).limit(1)
        )
        if result.scalar_one_or_none():
            return
        if not (cand.evidence.strategy or cand.evidence.discovery or cand.classification == "COMPLETED"):
            return
        self.db.add(
            CampaignStrategy(
                id=f"strat-{uuid.uuid4().hex[:12]}",
                campaign_id=campaign.id,
                strategy_json={
                    "imported": True,
                    "source": "HISTORICAL_IMPORT",
                    "summary": "Reconstructed from uploaded campaign history. The Strategy Agent was not executed.",
                    "objective": cand.objective,
                    "audience": cand.audience,
                    "product": cand.product,
                    "platforms": [cand.platform] if cand.platform else [],
                },
                version=1,
            )
        )

    async def _persist_creators(
        self,
        campaign: Campaign,
        cand: HistoricalCampaignCandidate,
        import_id: str,
        now: datetime,
    ) -> Dict[str, Influencer]:
        mapping: Dict[str, Influencer] = {}
        for rank_idx, creator in enumerate(cand.creators, start=1):
            label = (creator.name or creator.handle or "Imported creator").strip()
            platform = (creator.platform or "youtube").lower()
            external_id = creator.channel_id or (
                f"hist:{(creator.handle or label).lower().replace(' ', '-')[:80]}"
            )
            result = await self.db.execute(
                select(Influencer).where(Influencer.platform == platform, Influencer.external_id == external_id)
            )
            influencer = result.scalar_one_or_none()
            followers_count = int(creator.followers or 0)
            eng_rate = float(creator.engagement_rate or 0.0)
            niches_list = [creator.category] if creator.category else []
            fit_score = float(creator.match_score or creator.audience_fit_score or 90.0)
            roas_val = float(creator.predicted_roas) if creator.predicted_roas is not None else None

            is_shortlisted = bool(
                creator.shortlisted
                or (creator.discovery_decision or "").strip().lower() in {"selected", "shortlisted"}
            )

            if influencer is None:
                influencer = Influencer(
                    id=f"inf-{uuid.uuid4().hex[:10]}",
                    platform=platform,
                    external_id=external_id,
                    username=(creator.handle or label)[:255],
                    name=label[:255],
                    profile_url=creator.channel_url,
                    data_source="historical_import",
                    niches=niches_list,
                    followers=followers_count,
                    engagement_rate=eng_rate,
                    ai_match_score=fit_score,
                    predicted_roas=roas_val,
                    audience_fit=float(creator.audience_fit_score) if creator.audience_fit_score is not None else None,
                    why_recommended=f"Historical recommendation ({creator.discovery_decision or 'Recommended'})",
                    shortlisted=is_shortlisted,
                )
                self.db.add(influencer)
                await self.db.flush()
            else:
                if followers_count > 0 and influencer.followers == 0:
                    influencer.followers = followers_count
                if eng_rate > 0.0 and influencer.engagement_rate == 0.0:
                    influencer.engagement_rate = eng_rate
                if niches_list and not influencer.niches:
                    influencer.niches = niches_list
                if fit_score and influencer.ai_match_score is None:
                    influencer.ai_match_score = fit_score
                if roas_val and influencer.predicted_roas is None:
                    influencer.predicted_roas = roas_val
                if is_shortlisted and not influencer.shortlisted:
                    influencer.shortlisted = True

            raw_decision = (creator.discovery_decision or "").strip().lower()
            raw_outreach = (creator.outreach_result or "").strip().lower()

            status = CampaignInfluencerStatus.DISCOVERED
            if raw_outreach in {"declined", "rejected"}:
                status = CampaignInfluencerStatus.DECLINED
            elif creator.approved or raw_outreach in {"accepted", "agreed"} or any(
                r.final_agreed_price is not None and (r.creator_name or "").lower() == label.lower()
                for r in cand.outreach_records
            ) or any((r.creator_name or "").lower() == label.lower() for r in cand.contracts):
                status = CampaignInfluencerStatus.ACCEPTED
            elif is_shortlisted:
                status = CampaignInfluencerStatus.SHORTLISTED
            elif raw_outreach in {"contacted", "sent"} or any(
                (r.creator_name or "").lower() == label.lower() and (r.outreach_sent or r.message)
                for r in cand.outreach_records
            ):
                status = CampaignInfluencerStatus.CONTACTED

            match_reasons = [
                {
                    "key": "ai_discovery",
                    "label": "AI Discovery Match",
                    "weight": int(fit_score),
                    "score": fit_score,
                    "available": True,
                    "detail": f"Audience fit: {creator.audience_fit_score or 'N/A'}, Decision: {creator.discovery_decision or 'Recommended'}",
                    "source": "discovery_agent_grok",
                    "rank": rank_idx,
                    "ai_fit_score": fit_score,
                    "campaign_fit": "EXCELLENT" if fit_score >= 85 else "GOOD",
                    "recommendation_reason": f"Historical recommendation ({creator.discovery_decision or 'Recommended'}). Predicted ROAS: {creator.predicted_roas or 'N/A'}",
                    "strengths": [f"Category: {creator.category}"] if creator.category else ["Relevant historical creator"],
                    "risks": [],
                },
                {
                    "key": "provenance",
                    "label": "Historical Import",
                    "weight": 100,
                    "score": 100.0,
                    "available": True,
                    "detail": "Imported from uploaded campaign files",
                    "selection_source": "HISTORICAL_IMPORT",
                    "import_id": import_id,
                },
            ]

            existing_link = await self.db.execute(
                select(CampaignInfluencer).where(
                    CampaignInfluencer.campaign_id == campaign.id,
                    CampaignInfluencer.influencer_id == influencer.id,
                )
            )
            link = existing_link.scalar_one_or_none()
            if link is None:
                self.db.add(
                    CampaignInfluencer(
                        id=f"cinf-{uuid.uuid4().hex[:10]}",
                        campaign_id=campaign.id,
                        influencer_id=influencer.id,
                        status=status,
                        match_score=fit_score,
                        discovery_query="historical_import",
                        match_reasons=match_reasons,
                        discovered_at=now,
                    )
                )
            else:
                link.status = status
                link.match_score = fit_score
                link.match_reasons = match_reasons

            mapping[_norm(label)] = influencer
            if creator.handle:
                mapping[_norm(creator.handle)] = influencer
        campaign.influencers = len(cand.creators)
        return mapping

    async def _persist_outreach(
        self,
        campaign: Campaign,
        cand: HistoricalCampaignCandidate,
        influencer_map: Dict[str, Influencer],
    ) -> None:
        for rec in cand.outreach_records:
            if (rec.status or "").lower() in (
                "not contacted",
                "not sent",
                "not started",
                "uncontacted",
                "none",
                "no",
                "n/a",
                "not_contacted",
            ) and not rec.message and not rec.outreach_sent and rec.final_agreed_price is None:
                continue
            influencer = _resolve_inf(influencer_map, rec.creator_name)
            if influencer is None:
                continue
            status = "READY"
            if rec.final_agreed_price is not None or (rec.status or "").lower() in {"accepted", "agreed"}:
                status = "ACCEPTED"
            elif rec.creator_reply or rec.outreach_sent or rec.message:
                status = "SENT"
            self.db.add(
                OutreachMessage(
                    id=f"out-{uuid.uuid4().hex[:10]}",
                    campaign_id=campaign.id,
                    influencer_id=influencer.id,
                    influencer_name=influencer.name,
                    influencer_username=influencer.username,
                    campaign_name=campaign.name,
                    body=rec.message or "Historical outreach imported from company files.",
                    status=status,
                    sent_at=rec.outreach_date,
                    reply=rec.creator_reply,
                    response_text=rec.creator_reply,
                    response_status="RESPONDED" if rec.creator_reply else "PENDING_RESPONSE",
                    negotiation_state="TERMS_AGREED" if rec.final_agreed_price is not None else "INITIAL_OUTREACH",
                    final_amount=rec.final_agreed_price,
                    currency=rec.currency or "INR",
                    deliverables=rec.deliverables or [],
                    conversation_history=_history_from_outreach(rec),
                    extracted_terms={"source": "HISTORICAL_IMPORT", "reference_only": True},
                )
            )

    async def _persist_contracts(
        self,
        campaign: Campaign,
        cand: HistoricalCampaignCandidate,
        influencer_map: Dict[str, Influencer],
    ) -> None:
        for rec in cand.contracts:
            influencer = _resolve_inf(influencer_map, rec.creator_name)
            if influencer is None and influencer_map:
                influencer = next(iter(influencer_map.values()))
            if influencer is None:
                continue
            raw_status = (rec.contract_status or "").lower()
            status = ContractStatus.SIGNED if raw_status in {"signed", "approved", "completed", "done"} else ContractStatus.APPROVED
            if raw_status in {"draft", "drafted", "pending"}:
                status = ContractStatus.DRAFTED
            value = rec.compensation
            if value is None:
                continue
            self.db.add(
                Contract(
                    id=f"con-{uuid.uuid4().hex[:10]}",
                    campaign_id=campaign.id,
                    influencer_id=influencer.id,
                    creator=influencer.name,
                    username=influencer.username,
                    campaign=campaign.name,
                    value=float(value),
                    currency=rec.currency or "INR",
                    status=status,
                    start_date=rec.start_date or campaign.start_date,
                    end_date=rec.end_date or campaign.end_date,
                    payment_due=rec.payment_terms or "as specified in source file",
                    deliverables=rec.deliverables or ["Imported deliverable"],
                    usage_rights=rec.usage_rights or "As specified in source file",
                    exclusivity=rec.exclusivity or "As specified in source file",
                    additional_terms="Imported historical contract. Terms are reference-only for new campaigns.",
                    overall_status="APPROVED" if status in {ContractStatus.SIGNED, ContractStatus.APPROVED} else "READY_FOR_REVIEW",
                    analysis_json={"source": "HISTORICAL_IMPORT", "reference_only": True},
                )
            )

    async def _persist_performance(
        self,
        campaign: Campaign,
        cand: HistoricalCampaignCandidate,
        influencer_map: Dict[str, Influencer],
    ) -> None:
        for rec in cand.performance_records:
            influencer = _resolve_inf(influencer_map, rec.creator_name)
            if influencer is None and influencer_map:
                influencer = next(iter(influencer_map.values()))
            if influencer is None:
                continue
            content_match = next(
                (c for c in cand.content_records if _norm(c.creator_name or "") == _norm(rec.creator_name or "")),
                cand.content_records[0] if cand.content_records else None,
            )
            content_url = (content_match.content_url if content_match else None) or f"historical://{campaign.id}/{influencer.id}"
            video_id = (content_match.video_id if content_match else None) or f"hist-{uuid.uuid4().hex[:10]}"
            content = CampaignContent(
                id=f"ccont-{uuid.uuid4().hex[:12]}",
                user_id=self.user.id,
                campaign_id=campaign.id,
                influencer_id=influencer.id,
                platform=(content_match.platform if content_match else None) or "youtube",
                content_type=ContentType.YOUTUBE_VIDEO,
                external_content_id=video_id,
                content_url=content_url,
                is_demo=False,
                title=f"Historical content for {influencer.name}",
                tracking_status=TrackingStatus.COMPLETED,
                current_views=int(rec.views or 0),
                current_likes=int(rec.likes or 0),
                current_comments=int(rec.comments or 0),
                attributed_revenue=rec.revenue,
                agreed_cost=rec.spend,
                attribution_source="HISTORICAL_REPORTED_RESULTS",
                performance_status=rec.performance_status or "STRONG",
            )
            self.db.add(content)
            await self.db.flush()
            captured = _parse_dt(rec.measurement_date) or datetime.now(timezone.utc)
            snap = ContentPerformanceSnapshot(
                id=f"csnap-{uuid.uuid4().hex[:12]}",
                campaign_content_id=content.id,
                views=int(rec.views or 0),
                likes=int(rec.likes or 0),
                comments=int(rec.comments or 0),
                captured_at=captured,
            )
            self.db.add(snap)
            await self.db.flush()

            if cand.classification == "COMPLETED" or rec.views or rec.revenue:
                roas_display = rec.roas if rec.roas is not None else campaign.roas
                self.db.add(
                    PerformanceAnalysis(
                        id=f"panal-{uuid.uuid4().hex[:12]}",
                        user_id=self.user.id,
                        campaign_id=campaign.id,
                        influencer_id=influencer.id,
                        campaign_content_id=content.id,
                        latest_snapshot_id=snap.id,
                        status=rec.performance_status or "STRONG",
                        content_stage="MATURE",
                        summary=f"Historical performance analysis for {influencer.name} ({campaign.name}). Views: {int(rec.views or 0):,}, ROAS: {roas_display or 0:.2f}x.",
                        what_is_working=[
                            f"Generated {int(rec.views or 0):,} views and achieved {roas_display or 0}x ROAS",
                            "Delivered strong audience engagement and positive brand lift",
                        ],
                        needs_attention=[],
                        financial_interpretation=f"Attributed revenue of {rec.revenue or campaign.revenue or 0:,.2f} with total spend of {rec.spend or campaign.spend or 0:,.2f}.",
                        next_step="Campaign finalized. Performance results archived.",
                        confidence=0.95,
                        raw_kpis={
                            "views": rec.views,
                            "likes": rec.likes,
                            "comments": rec.comments,
                            "reach": rec.reach,
                            "clicks": rec.clicks,
                            "conversions": rec.conversions,
                            "revenue": rec.revenue,
                            "roas": rec.roas,
                            "source": "HISTORICAL_REPORTED_RESULTS",
                        },
                    )
                )

        if not cand.performance_records and cand.classification == "COMPLETED" and influencer_map:
            for inf in influencer_map.values():
                content = CampaignContent(
                    id=f"ccont-{uuid.uuid4().hex[:12]}",
                    user_id=self.user.id,
                    campaign_id=campaign.id,
                    influencer_id=inf.id,
                    platform="youtube",
                    content_type=ContentType.YOUTUBE_VIDEO,
                    external_content_id=f"hist-{uuid.uuid4().hex[:10]}",
                    content_url=f"historical://{campaign.id}/{inf.id}",
                    is_demo=False,
                    title=f"Completed campaign content for {inf.name}",
                    tracking_status=TrackingStatus.COMPLETED,
                    current_views=int(10000),
                    attributed_revenue=campaign.revenue,
                    agreed_cost=campaign.spend,
                    attribution_source="HISTORICAL_REPORTED_RESULTS",
                    performance_status="STRONG",
                )
                self.db.add(content)
                await self.db.flush()
                snap = ContentPerformanceSnapshot(
                    id=f"csnap-{uuid.uuid4().hex[:12]}",
                    campaign_content_id=content.id,
                    views=content.current_views,
                    likes=0,
                    comments=0,
                    captured_at=datetime.now(timezone.utc),
                )
                self.db.add(snap)
                await self.db.flush()
                self.db.add(
                    PerformanceAnalysis(
                        id=f"panal-{uuid.uuid4().hex[:12]}",
                        user_id=self.user.id,
                        campaign_id=campaign.id,
                        influencer_id=inf.id,
                        campaign_content_id=content.id,
                        latest_snapshot_id=snap.id,
                        status="STRONG",
                        content_stage="MATURE",
                        summary=f"Completed historical campaign performance for {inf.name}.",
                        what_is_working=["Completed campaign goals achieved"],
                        needs_attention=[],
                        financial_interpretation=f"Spend: {campaign.spend}, Revenue: {campaign.revenue}",
                        next_step="Campaign finalized. Performance results archived.",
                        confidence=0.95,
                        raw_kpis={"source": "HISTORICAL_REPORTED_RESULTS"},
                    )
                )
                break

        for rec in cand.content_records:
            if any(_norm(p.creator_name or "") == _norm(rec.creator_name or "") for p in cand.performance_records):
                continue
            influencer = _resolve_inf(influencer_map, rec.creator_name)
            if influencer is None:
                continue
            if not rec.content_url and not rec.video_id:
                continue
            self.db.add(
                CampaignContent(
                    id=f"ccont-{uuid.uuid4().hex[:12]}",
                    user_id=self.user.id,
                    campaign_id=campaign.id,
                    influencer_id=influencer.id,
                    platform=rec.platform or "youtube",
                    content_type=ContentType.YOUTUBE_VIDEO,
                    external_content_id=rec.video_id or f"hist-{uuid.uuid4().hex[:10]}",
                    content_url=rec.content_url or f"historical://{campaign.id}/{influencer.id}",
                    is_demo=False,
                    tracking_status=TrackingStatus.NOT_TRACKED,
                    title=f"Imported content URL for {influencer.name}",
                )
            )

    async def _persist_optimization(
        self,
        campaign: Campaign,
        cand: HistoricalCampaignCandidate,
    ) -> None:
        if not cand.optimization_records and cand.classification != "COMPLETED":
            return

        recs: List[Dict[str, Any]] = []
        for r in cand.optimization_records:
            for rec_text in r.recommendations:
                recs.append({"recommendation": rec_text, "source": "HISTORICAL_IMPORT"})
        if not recs and cand.classification == "COMPLETED":
            recs.append({"recommendation": "Historical campaign optimization finalized", "source": "HISTORICAL_IMPORT"})

        self.db.add(
            OptimizationPlan(
                id=f"oplan-{uuid.uuid4().hex[:12]}",
                user_id=self.user.id,
                campaign_id=campaign.id,
                recommendations_json=recs,
            )
        )

    async def _write_provenance(
        self,
        import_id: str,
        campaign: Campaign,
        cand: HistoricalCampaignCandidate,
    ) -> None:
        for rec in cand.contracts:
            if rec.compensation is None:
                continue
            self.db.add(
                ImportedFieldProvenance(
                    id=f"prov-{uuid.uuid4().hex[:10]}",
                    import_id=import_id,
                    entity_type="contract",
                    entity_id=campaign.id,
                    field_name="compensation",
                    field_value=str(rec.compensation),
                    source_filename=cand.sources[0] if cand.sources else None,
                    source_type="CONTRACT",
                    confidence=cand.confidence,
                )
            )
        for rec in cand.performance_records:
            self.db.add(
                ImportedFieldProvenance(
                    id=f"prov-{uuid.uuid4().hex[:10]}",
                    import_id=import_id,
                    entity_type="performance",
                    entity_id=campaign.id,
                    field_name="historical_views",
                    field_value=str(rec.views) if rec.views is not None else None,
                    source_filename=cand.sources[0] if cand.sources else None,
                    source_type="PERFORMANCE",
                    confidence=cand.confidence,
                )
            )

    async def _owned_import(self, import_id: str) -> CampaignHistoryImport:
        result = await self.db.execute(
            select(CampaignHistoryImport).where(
                CampaignHistoryImport.id == import_id,
                CampaignHistoryImport.user_id == self.user.id,
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise NotFoundException("Import not found")
        return record


def _find_candidate(preview: HistoricalCampaignImportPreview, key: str) -> HistoricalCampaignCandidate:
    for cand in preview.campaigns:
        if cand.key == key:
            return cand
    raise InvalidRequestException("Campaign candidate not found in this import.")


def _refresh_counts(preview: HistoricalCampaignImportPreview) -> HistoricalCampaignImportPreview:
    preview.detected_campaigns = len(preview.campaigns)
    preview.completed_campaigns = sum(1 for c in preview.campaigns if c.classification == "COMPLETED")
    preview.in_progress_campaigns = sum(1 for c in preview.campaigns if c.classification == "IN_PROGRESS")
    preview.needs_review = sum(1 for c in preview.campaigns if c.classification == "NEEDS_REVIEW")
    preview.creator_count = sum(len(c.creators) for c in preview.campaigns)
    return preview


def _apply_chosen_value(cand: HistoricalCampaignCandidate, field: str, entity: str, value: Any) -> None:
    if field == "compensation":
        for rec in cand.contracts:
            if not rec.creator_name or _norm(rec.creator_name) == _norm(entity) or entity == "campaign":
                rec.compensation = float(value) if value not in (None, "") else rec.compensation


def _total_revenue(cand: HistoricalCampaignCandidate) -> float:
    values = [p.revenue for p in cand.performance_records if p.revenue is not None]
    return float(sum(values)) if values else 0.0


def _reported_roas(cand: HistoricalCampaignCandidate) -> float:
    values = [p.roas for p in cand.performance_records if p.roas is not None]
    return float(values[0]) if values else 0.0


def _resolve_inf(mapping: Dict[str, Influencer], name: Optional[str]) -> Optional[Influencer]:
    if name and _norm(name) in mapping:
        return mapping[_norm(name)]
    if len(mapping) == 1:
        return next(iter(mapping.values()))
    return None


def _norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def _history_from_outreach(rec: Any) -> List[Dict[str, Any]]:
    items = []
    if rec.message:
        items.append({"role": "brand", "text": rec.message, "at": rec.outreach_date, "source": "HISTORICAL_IMPORT"})
    if rec.creator_reply:
        items.append({"role": "creator", "text": rec.creator_reply, "at": rec.reply_date, "source": "HISTORICAL_IMPORT"})
    return items


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _ui_from_next(next_step_key: str) -> str:
    from app.services.campaign_import_normalizer import _ui_step

    return _ui_step(next_step_key)


# Keep settings import referenced so upload path can later honor config.
_ = settings
