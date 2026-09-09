import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.execution import AgentExecutionService
from app.ai.agents.optimization import OptimizationAgent
from app.ai.agents.performance import PerformanceAgent
from app.ai.workflow_states import AgentRunStatus
from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.approval import Approval
from app.models.campaign import Campaign
from app.models.campaign_activity import CampaignActivity
from app.models.campaign_content import (
    CampaignContent,
    ContentPerformanceSnapshot,
    OptimizationPlan,
    PerformanceAnalysis,
)
from app.models.campaign_influencer import CampaignInfluencer
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.campaign_content import (
    AttributionUpdateRequest,
    CampaignContentResponse,
    DecideOptimizationRequest,
    OptimizationPlanResponse,
    OptimizationRecommendationSchema,
    PerformanceAnalysisResponse,
    SnapshotResponse,
    TrackContentRequest,
)
from app.services.content_tracking_service import ContentTrackingService

router = APIRouter(prefix="/campaigns/{campaign_id}/content", tags=["Campaign Content Tracking"])


async def _get_owned_campaign(campaign_id: str, user: User, db: AsyncSession) -> Campaign:
    stmt = select(Campaign).where(Campaign.id == campaign_id, Campaign.owner_id == user.id)
    res = await db.execute(stmt)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise NotFoundException(detail=f"Campaign '{campaign_id}' not found or not accessible.")
    return campaign


def _norm_dt(dt: Optional[datetime]) -> datetime:
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _build_content_response(content: CampaignContent, influencer: Optional[Influencer] = None) -> CampaignContentResponse:
    snapshots = [
        SnapshotResponse.model_validate(s)
        for s in sorted(content.snapshots or [], key=lambda x: _norm_dt(x.captured_at), reverse=True)
    ]

    return CampaignContentResponse(
        id=content.id,
        campaign_id=content.campaign_id,
        influencer_id=content.influencer_id,
        influencer_name=influencer.name if influencer else (content.influencer.name if content.influencer else None),
        influencer_username=influencer.username if influencer else (content.influencer.username if content.influencer else None),
        influencer_avatar=influencer.avatar if influencer else (content.influencer.avatar if content.influencer else None),
        platform=content.platform,
        content_type=content.content_type,
        external_content_id=content.external_content_id,
        content_url=content.content_url,
        title=content.title,
        thumbnail_url=content.thumbnail_url,
        channel_id=content.channel_id,
        channel_title=content.channel_title,
        published_at=content.published_at,
        duration_seconds=content.duration_seconds,
        tracking_status=content.tracking_status,
        agreed_cost=content.agreed_cost,
        currency=content.currency,
        last_sync_at=content.last_sync_at,
        sync_error=content.sync_error,
        baseline_median_views=content.baseline_median_views,
        baseline_avg_views=content.baseline_avg_views,
        baseline_avg_likes=content.baseline_avg_likes,
        baseline_avg_comments=content.baseline_avg_comments,
        baseline_engagement_rate=content.baseline_engagement_rate,
        baseline_sample_size=content.baseline_sample_size,
        current_views=content.current_views,
        current_likes=content.current_likes,
        current_comments=content.current_comments,
        engagement_rate=content.engagement_rate,
        performance_lift_percent=content.performance_lift_percent,
        cost_per_view=content.cost_per_view,
        cpm=content.cpm,
        cost_per_engagement=content.cost_per_engagement,
        engagement_lift_percent=content.engagement_lift_percent,
        performance_status=content.performance_status,
        attributed_orders=content.attributed_orders,
        average_order_value=content.average_order_value,
        attributed_revenue=content.attributed_revenue,
        gross_margin_percent=content.gross_margin_percent,
        attributed_profit=content.attributed_profit,
        attribution_source=content.attribution_source,
        attribution_updated_at=content.attribution_updated_at,
        roas=content.roas,
        roi=content.roi,
        content_age_hours=content.content_age_hours,
        content_age_days=content.content_age_days,
        content_stage=content.content_stage,
        momentum=content.momentum,
        is_demo=content.is_demo if content.is_demo is not None else False,
        snapshots=snapshots,
        created_at=content.created_at,
        updated_at=content.updated_at,
    )


@router.post("/track", response_model=CampaignContentResponse, summary="Register & track YouTube video or Short URL")
async def track_campaign_content(
    campaign_id: str,
    payload: TrackContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = await _get_owned_campaign(campaign_id, current_user, db)

    # Verify influencer exists and is associated with this campaign or exists on platform
    inf_stmt = select(Influencer).where(Influencer.id == payload.influencer_id)
    inf_res = await db.execute(inf_stmt)
    influencer = inf_res.scalar_one_or_none()
    if not influencer:
        raise NotFoundException(detail=f"Influencer '{payload.influencer_id}' not found.")

    tracking_service = ContentTrackingService(db)
    content = await tracking_service.track_content(
        campaign=campaign,
        influencer=influencer,
        content_url=payload.content_url,
        content_type_override=payload.content_type,
    )

    return _build_content_response(content, influencer)


@router.get("", response_model=List[CampaignContentResponse], summary="List tracked campaign content")
async def list_campaign_content(
    campaign_id: str,
    influencer_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    stmt = (
        select(CampaignContent)
        .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
        .where(CampaignContent.campaign_id == campaign_id)
    )
    if influencer_id:
        stmt = stmt.where(CampaignContent.influencer_id == influencer_id)
    stmt = stmt.order_by(CampaignContent.created_at.desc())

    res = await db.execute(stmt)
    items = res.scalars().all()

    return [_build_content_response(item) for item in items]


@router.post("/{content_id}/refresh", response_model=CampaignContentResponse, summary="Refresh live metrics from YouTube API")
async def refresh_content_metrics(
    campaign_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    # Verify content belongs to this campaign
    c_stmt = (
        select(CampaignContent)
        .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
        .where(CampaignContent.id == content_id, CampaignContent.campaign_id == campaign_id)
    )
    c_res = await db.execute(c_stmt)
    content = c_res.scalar_one_or_none()
    if not content:
        raise NotFoundException(detail=f"Tracked content '{content_id}' not found for this campaign.")

    tracking_service = ContentTrackingService(db)
    updated = await tracking_service.refresh_content_metrics(content_id)

    # Reload with relationships
    c_res2 = await db.execute(c_stmt)
    reloaded = c_res2.scalar_one()
    return _build_content_response(reloaded)


@router.get("/{content_id}/snapshots", response_model=List[SnapshotResponse], summary="List historical performance snapshots")
async def list_content_snapshots(
    campaign_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    snap_stmt = (
        select(ContentPerformanceSnapshot)
        .join(CampaignContent, ContentPerformanceSnapshot.campaign_content_id == CampaignContent.id)
        .where(
            CampaignContent.campaign_id == campaign_id,
            ContentPerformanceSnapshot.campaign_content_id == content_id,
        )
        .order_by(ContentPerformanceSnapshot.captured_at.asc())
    )
    res = await db.execute(snap_stmt)
    snapshots = res.scalars().all()
    return [SnapshotResponse.model_validate(s) for s in snapshots]


@router.post(
    "/{content_id}/attribution",
    response_model=CampaignContentResponse,
    summary="Save verified campaign business attribution",
)
async def update_content_attribution(
    campaign_id: str,
    content_id: str,
    payload: AttributionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    # Verify content belongs to this campaign
    c_stmt = select(CampaignContent).where(
        CampaignContent.id == content_id, CampaignContent.campaign_id == campaign_id
    )
    c_res = await db.execute(c_stmt)
    content = c_res.scalar_one_or_none()
    if not content:
        raise NotFoundException(detail=f"Tracked content '{content_id}' not found for this campaign.")

    tracking_service = ContentTrackingService(db)
    updated = await tracking_service.update_content_attribution(
        content_id=content_id,
        attributed_revenue=payload.attributed_revenue,
        attributed_orders=payload.attributed_orders,
        average_order_value=payload.average_order_value,
        gross_margin_percent=payload.gross_margin_percent,
        attributed_profit=payload.attributed_profit,
        attribution_source=payload.attribution_source,
    )

    # Reload with influencer and snapshots
    load_stmt = (
        select(CampaignContent)
        .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
        .where(CampaignContent.id == content_id)
    )
    res = await db.execute(load_stmt)
    reloaded = res.scalar_one()

    return _build_content_response(reloaded)


async def _enrich_plan_with_approvals(plan: OptimizationPlan, db: AsyncSession) -> OptimizationPlanResponse:
    recs = [dict(r) for r in (plan.recommendations_json or [])]
    appr_ids = [r.get("approval_id") or r.get("id") for r in recs if r.get("approval_id") or r.get("id")]
    if appr_ids:
        res = await db.execute(select(Approval).where(Approval.id.in_(appr_ids)))
        approvals_by_id = {a.id: a for a in res.scalars().all()}
        for r in recs:
            a_id = r.get("approval_id") or r.get("id")
            if a_id in approvals_by_id:
                r["status"] = approvals_by_id[a_id].status

    return OptimizationPlanResponse(
        id=plan.id,
        campaign_id=plan.campaign_id,
        campaign_content_id=plan.campaign_content_id,
        performance_analysis_id=plan.performance_analysis_id,
        agent_run_id=plan.agent_run_id,
        status=plan.status,
        recommendations=[OptimizationRecommendationSchema.model_validate(r) for r in recs],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


@router.post(
    "/{content_id}/performance",
    response_model=PerformanceAnalysisResponse,
    summary="Run Performance Agent on tracked content",
)
async def analyze_content_performance(
    campaign_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = await _get_owned_campaign(campaign_id, current_user, db)

    # 1. Fetch tracked content
    c_stmt = (
        select(CampaignContent)
        .options(selectinload(CampaignContent.snapshots), selectinload(CampaignContent.influencer))
        .where(CampaignContent.id == content_id, CampaignContent.campaign_id == campaign_id)
    )
    c_res = await db.execute(c_stmt)
    content = c_res.scalar_one_or_none()
    if not content:
        raise NotFoundException(detail=f"Tracked content '{content_id}' not found.")

    # 2. Run Performance Agent via AgentExecutionService
    exec_service = AgentExecutionService(db)
    agent = PerformanceAgent()
    run = await exec_service.run(
        agent=agent,
        user=current_user,
        campaign=campaign,
        trigger="manual",
        extras={"content_id": content.id},
    )

    if run.status == AgentRunStatus.FAILED:
        raise BadRequestException(detail=run.error_message or "Performance Agent execution failed.")

    perf_data = run.output_json.get("data", {}) if run.output_json else {}

    # 3. Create and persist PerformanceAnalysis record
    analysis = PerformanceAnalysis(
        id=f"panal-{uuid.uuid4().hex[:12]}",
        campaign_id=campaign_id,
        influencer_id=content.influencer_id,
        campaign_content_id=content.id,
        latest_snapshot_id=content.snapshots[0].id if content.snapshots else None,
        agent_run_id=run.id,
        user_id=current_user.id,
        status=perf_data.get("status", "ON_TRACK"),
        content_stage=perf_data.get("content_stage", content.content_stage or "EARLY_STAGE"),
        summary=perf_data.get("summary", run.output_json.get("summary", "") if run.output_json else ""),
        what_is_working=perf_data.get("what_is_working", []),
        needs_attention=perf_data.get("needs_attention", []),
        financial_interpretation=perf_data.get("financial_interpretation", ""),
        next_step=perf_data.get("next_step", ""),
        confidence=float(perf_data.get("confidence", 0.9)),
        raw_kpis={
            "current_views": content.current_views,
            "current_likes": content.current_likes,
            "current_comments": content.current_comments,
            "engagement_rate": content.engagement_rate,
            "performance_lift_percent": content.performance_lift_percent,
            "cost_per_view": content.cost_per_view,
            "cpm": content.cpm,
            "cost_per_engagement": content.cost_per_engagement,
            "attributed_revenue": content.attributed_revenue,
            "gross_margin_percent": content.gross_margin_percent,
            "attributed_profit": content.attributed_profit,
            "roas": content.roas,
            "roi": content.roi,
            "content_age_hours": content.content_age_hours,
            "content_stage": content.content_stage,
            "momentum": content.momentum,
        },
    )
    db.add(analysis)

    # Activity log
    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=campaign_id,
        activity_type="PERFORMANCE_ANALYSIS",
        title="Performance Agent Analysis Generated",
        description=f"Performance Agent evaluated '{content.title or content.content_url}' — Status: {analysis.status}",
        metadata_json={
            "content_id": content.id,
            "status": analysis.status,
            "summary": analysis.summary[:200],
        },
    )
    db.add(activity)

    await db.commit()
    await db.refresh(analysis)
    return PerformanceAnalysisResponse.model_validate(analysis)


@router.get(
    "/performance/latest",
    response_model=Optional[PerformanceAnalysisResponse],
    summary="Get latest Performance Agent analysis for campaign",
)
async def get_latest_campaign_performance(
    campaign_id: str,
    content_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    stmt = select(PerformanceAnalysis).where(PerformanceAnalysis.campaign_id == campaign_id)
    if content_id:
        stmt = stmt.where(PerformanceAnalysis.campaign_content_id == content_id)
    stmt = stmt.order_by(PerformanceAnalysis.created_at.desc()).limit(1)

    res = await db.execute(stmt)
    analysis = res.scalar_one_or_none()
    if not analysis:
        return None
    return PerformanceAnalysisResponse.model_validate(analysis)


@router.get(
    "/{content_id}/performance",
    response_model=Optional[PerformanceAnalysisResponse],
    summary="Get latest Performance Agent analysis for content",
)
async def get_content_performance(
    campaign_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    stmt = (
        select(PerformanceAnalysis)
        .where(
            PerformanceAnalysis.campaign_id == campaign_id,
            PerformanceAnalysis.campaign_content_id == content_id,
        )
        .order_by(PerformanceAnalysis.created_at.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    analysis = res.scalar_one_or_none()
    if not analysis:
        return None
    return PerformanceAnalysisResponse.model_validate(analysis)


@router.post(
    "/{content_id}/optimization",
    response_model=OptimizationPlanResponse,
    summary="Run Optimization Agent on tracked content",
)
async def generate_content_optimization(
    campaign_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = await _get_owned_campaign(campaign_id, current_user, db)

    # 1. Verify latest performance analysis exists
    p_stmt = (
        select(PerformanceAnalysis)
        .where(
            PerformanceAnalysis.campaign_id == campaign_id,
            PerformanceAnalysis.campaign_content_id == content_id,
        )
        .order_by(PerformanceAnalysis.created_at.desc())
        .limit(1)
    )
    p_res = await db.execute(p_stmt)
    perf_analysis = p_res.scalar_one_or_none()
    if not perf_analysis:
        raise BadRequestException(
            detail="Performance Agent analysis must be completed before running the Optimization Agent."
        )

    # 2. Run Optimization Agent via AgentExecutionService
    exec_service = AgentExecutionService(db)
    agent = OptimizationAgent()
    run = await exec_service.run(
        agent=agent,
        user=current_user,
        campaign=campaign,
        trigger="manual",
        extras={"content_id": content_id},
    )

    if run.status == AgentRunStatus.FAILED:
        raise BadRequestException(detail=run.error_message or "Optimization Agent execution failed.")

    opt_data = run.output_json.get("data", {}) if run.output_json else {}
    raw_recs = opt_data.get("recommendations", [])[:3]

    # 3. Create Approval records for each recommendation
    plan_id = f"opt-{uuid.uuid4().hex[:12]}"
    enriched_recs = []

    for r in raw_recs:
        appr_id = f"appr-{uuid.uuid4().hex[:8]}"
        approval = Approval(
            id=appr_id,
            agent="Optimization Agent",
            type=r.get("category", "OPTIMIZATION"),
            action=r.get("action", ""),
            reason=r.get("reason", ""),
            campaign=campaign.name,
            financial_impact=f"Priority: {r.get('priority', 'MEDIUM')}",
            confidence=0.92,
            timestamp="Just now",
            status="pending",
            user_id=current_user.id,
            campaign_id=campaign.id,
            agent_run_id=run.id,
        )
        db.add(approval)

        rec_item = dict(r)
        rec_item["id"] = appr_id
        rec_item["approval_id"] = appr_id
        rec_item["status"] = "pending"
        enriched_recs.append(rec_item)

    # 4. Create and persist OptimizationPlan
    plan = OptimizationPlan(
        id=plan_id,
        campaign_id=campaign_id,
        campaign_content_id=content_id,
        performance_analysis_id=perf_analysis.id,
        agent_run_id=run.id,
        user_id=current_user.id,
        recommendations_json=enriched_recs,
    )
    db.add(plan)

    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=campaign_id,
        activity_type="OPTIMIZATION_PLAN",
        title="Optimization Recommendations Generated",
        description=f"Generated {len(enriched_recs)} optimization recommendations submitted to Approval Center.",
        metadata_json={
            "plan_id": plan.id,
            "recommendation_count": len(enriched_recs),
        },
    )
    db.add(activity)

    await db.commit()
    await db.refresh(plan)

    return await _enrich_plan_with_approvals(plan, db)


@router.get(
    "/optimization/latest",
    response_model=Optional[OptimizationPlanResponse],
    summary="Get latest Optimization plan for campaign",
)
async def get_latest_campaign_optimization(
    campaign_id: str,
    content_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    stmt = select(OptimizationPlan).where(OptimizationPlan.campaign_id == campaign_id)
    if content_id:
        stmt = stmt.where(OptimizationPlan.campaign_content_id == content_id)
    stmt = stmt.order_by(OptimizationPlan.created_at.desc()).limit(1)

    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        return None
    return await _enrich_plan_with_approvals(plan, db)


@router.get(
    "/{content_id}/optimization",
    response_model=Optional[OptimizationPlanResponse],
    summary="Get latest Optimization plan for content",
)
async def get_content_optimization(
    campaign_id: str,
    content_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _get_owned_campaign(campaign_id, current_user, db)

    stmt = (
        select(OptimizationPlan)
        .where(
            OptimizationPlan.campaign_id == campaign_id,
            OptimizationPlan.campaign_content_id == content_id,
        )
        .order_by(OptimizationPlan.created_at.desc())
        .limit(1)
    )
    res = await db.execute(stmt)
    plan = res.scalar_one_or_none()
    if not plan:
        return None
    return await _enrich_plan_with_approvals(plan, db)


@router.post(
    "/optimization/decide",
    response_model=OptimizationPlanResponse,
    summary="Decide on an optimization recommendation item",
)
async def decide_optimization_recommendation(
    campaign_id: str,
    payload: DecideOptimizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = await _get_owned_campaign(campaign_id, current_user, db)

    # 1. Fetch approval item
    appr_stmt = select(Approval).where(
        Approval.id == payload.approval_id,
        Approval.campaign_id == campaign_id,
        Approval.user_id == current_user.id,
    )
    appr_res = await db.execute(appr_stmt)
    approval = appr_res.scalar_one_or_none()
    if not approval:
        raise NotFoundException(detail=f"Approval item '{payload.approval_id}' not found.")

    approval.status = payload.decision
    approval.decision_reason = payload.reason
    approval.reviewed_at = datetime.now(timezone.utc)
    approval.resolved_by = current_user.id

    # 2. Activity log
    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=campaign_id,
        activity_type="APPROVAL_DECIDED",
        title=f"Optimization Recommendation {payload.decision.capitalize()}",
        description=f"Action '{approval.action[:60]}' marked as {payload.decision}.",
        metadata_json={
            "approval_id": approval.id,
            "decision": payload.decision,
            "reason": payload.reason,
        },
    )
    db.add(activity)

    await db.commit()

    # 3. Return the latest plan refreshed
    plan_stmt = (
        select(OptimizationPlan)
        .where(OptimizationPlan.campaign_id == campaign_id)
        .order_by(OptimizationPlan.created_at.desc())
        .limit(1)
    )
    plan_res = await db.execute(plan_stmt)
    plan = plan_res.scalar_one_or_none()
    if not plan:
        raise NotFoundException(detail="No optimization plan found.")

    return await _enrich_plan_with_approvals(plan, db)

