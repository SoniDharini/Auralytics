import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, InvalidRequestException
from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.campaign import Campaign
from app.models.campaign_activity import CampaignActivity
from app.models.campaign_influencer import CampaignInfluencer
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.campaign import (
    CampaignActivityResponse,
    CampaignCreate,
    CampaignResponse,
    CampaignUpdate,
)
from app.schemas.campaign_workflow import CampaignWorkflowResponse
from app.schemas.influencer import (
    InfluencerFetchRequest,
    InfluencerFetchResponse,
    InfluencerResponse,
    ProviderResultSchema,
)
from app.services.campaign_workflow_service import CampaignWorkflowService
from app.services.campaign_metrics_service import reconcile_campaign_metrics
from app.services.creator_discovery_service import CreatorDiscoveryService, discover_for_campaign_with_retry

router = APIRouter(prefix="/campaigns", tags=["Campaigns"])


def _workspace_brand(user: User) -> str:
    name = (user.company_name or "").strip()
    return name[:255] if name else "GlowNaturals"


def _campaign_types_for_storage(types: Optional[List[str]]) -> Optional[List[str]]:
    if types is None:
        return None
    cleaned = [t.strip() for t in types if t and t.strip().lower() != "other"]
    return cleaned


@router.get("", response_model=List[CampaignResponse], summary="List all campaigns for current user")
async def list_campaigns(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(Campaign.owner_id == current_user.id)
    if status and status != "all":
        stmt = stmt.where(Campaign.status == status)

    result = await db.execute(stmt)
    campaigns = result.scalars().all()
    reconciled = [await reconcile_campaign_metrics(c, db) for c in campaigns]
    return [CampaignResponse.model_validate(c) for c in reconciled]


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED, summary="Create a new campaign")
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    camp_id = f"camp-{uuid.uuid4().hex[:8]}"

    campaign = Campaign(
        id=camp_id,
        owner_id=current_user.id,
        name=data.name,
        brand=_workspace_brand(current_user),
        status=data.status,
        health=data.health,
        budget=data.budget,
        spend=0.0,
        revenue=0.0,
        roas=0.0,
        influencers=0,
        progress=0,
        start_date=data.start_date,
        end_date=data.end_date,
        conversions=0,
        reach=0,
        objective=data.objective,
        description=data.description,
        campaign_types=_campaign_types_for_storage(data.campaign_types),
        target_locations=data.target_locations,
        target_age_min=data.target_age_min,
        target_age_max=data.target_age_max,
        target_gender=data.target_gender,
        interests=data.interests,
        languages=data.languages,
        platforms=data.platforms,
        creator_tiers=data.creator_tiers,
        budget_allocation=data.budget_allocation,
        primary_kpi=data.primary_kpi,
        target_roas=data.target_roas,
        target_cpa=data.target_cpa,
        keywords=data.keywords,
        min_followers=data.min_followers,
        max_followers=data.max_followers,
    )
    db.add(campaign)

    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=camp_id,
        activity_type="CAMPAIGN_CREATED",
        title=f"Campaign '{campaign.name}' created",
        description=f"Created campaign for brand '{campaign.brand}' with budget ₹{campaign.budget:,.0f}.",
        metadata_json={"campaign_name": campaign.name, "brand": campaign.brand, "budget": campaign.budget},
    )
    db.add(activity)

    await db.commit()
    await db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


@router.get("/{campaign_id}", response_model=CampaignResponse, summary="Get a campaign by ID")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    campaign = await reconcile_campaign_metrics(campaign, db)
    return CampaignResponse.model_validate(campaign)


@router.get(
    "/{campaign_id}/workflow",
    response_model=CampaignWorkflowResponse,
    summary="Read-only campaign journey: completed steps, current step, and next action",
)
async def get_campaign_workflow(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    return await CampaignWorkflowService(db).get_state(campaign)


@router.post(
    "/{campaign_id}/complete",
    response_model=CampaignResponse,
    summary="Explicitly complete a campaign after Optimization. Does not delete history.",
)
async def complete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.ai.workflow_states import WorkflowState

    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    if campaign.status == "completed" or campaign.workflow_state == WorkflowState.COMPLETED:
        raise InvalidRequestException(detail="Campaign is already completed.")

    wf = CampaignWorkflowService(db)
    has_performance = await wf._has_performance_analysis(campaign.id)
    has_optimization = await wf._has_optimization_plan(campaign.id)
    pending_opt = await wf._count_pending_optimization_approvals(campaign.id)

    if not has_performance:
        raise InvalidRequestException(
            detail="Performance analysis is required before completing the campaign."
        )
    if not has_optimization:
        raise InvalidRequestException(
            detail="Optimization must run before completing the campaign."
        )
    if pending_opt > 0:
        raise InvalidRequestException(
            detail="Resolve pending optimization approvals before completing the campaign."
        )

    previous_status = campaign.status
    campaign.status = "completed"
    campaign.workflow_state = WorkflowState.COMPLETED
    campaign.progress = 100

    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=campaign.id,
        activity_type="CAMPAIGN_COMPLETED",
        title=f"Campaign '{campaign.name}' completed",
        description="Campaign marked completed. Performance and Optimization history remain available.",
        metadata_json={"previous_status": previous_status},
    )
    db.add(activity)
    await db.commit()
    await db.refresh(campaign)
    campaign = await reconcile_campaign_metrics(campaign, db)
    return CampaignResponse.model_validate(campaign)


@router.patch("/{campaign_id}", response_model=CampaignResponse, summary="Update a campaign")
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    old_budget = campaign.budget
    old_status = campaign.status

    update_dict = data.model_dump(exclude_unset=True)
    update_dict.pop("brand", None)
    if "campaign_types" in update_dict:
        update_dict["campaign_types"] = _campaign_types_for_storage(update_dict["campaign_types"])
    for field, value in update_dict.items():
        setattr(campaign, field, value)

    if (
        campaign.target_age_min is not None
        and campaign.target_age_max is not None
        and campaign.target_age_min > campaign.target_age_max
    ):
        raise InvalidRequestException("Maximum age must be greater than or equal to minimum age.")

    # Determine activity description
    if "status" in update_dict and update_dict["status"] != old_status:
        activity_type = "CAMPAIGN_STATUS_CHANGED"
        title = f"Campaign '{campaign.name}' status changed to {campaign.status.upper()}"
        description = f"Status transitioned from {old_status} to {campaign.status}."
    elif "budget" in update_dict and update_dict["budget"] != old_budget:
        activity_type = "CAMPAIGN_UPDATED"
        title = f"Campaign '{campaign.name}' budget updated"
        description = f"Budget updated from ₹{old_budget:,.0f} to ₹{campaign.budget:,.0f}."
    else:
        activity_type = "CAMPAIGN_UPDATED"
        title = f"Campaign '{campaign.name}' updated"
        fields_str = ", ".join(update_dict.keys())
        description = f"Modified fields: {fields_str}."

    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=campaign.id,
        activity_type=activity_type,
        title=title,
        description=description,
        metadata_json=update_dict,
    )
    db.add(activity)

    await db.commit()
    await db.refresh(campaign)
    return CampaignResponse.model_validate(campaign)


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a campaign")
async def delete_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    result = await db.execute(stmt)
    campaign = result.scalar_one_or_none()

    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    camp_name = campaign.name

    from sqlalchemy import delete
    from app.models.agent_execution import AgentRun
    from app.models.approval import Approval
    from app.models.campaign_content import (
        CampaignContent,
        ContentPerformanceSnapshot,
        OptimizationPlan,
        PerformanceAnalysis,
    )
    from app.models.campaign_history_import import ImportedFieldProvenance
    from app.models.campaign_influencer import CampaignInfluencer
    from app.models.campaign_strategy import CampaignStrategy
    from app.models.contract import Contract
    from app.models.outreach import OutreachMessage

    # 1. Clean up campaign-specific records (shared global influencers are preserved intact)
    await db.execute(delete(Contract).where(Contract.campaign_id == campaign_id))
    await db.execute(delete(OutreachMessage).where(OutreachMessage.campaign_id == campaign_id))
    await db.execute(delete(Approval).where(Approval.campaign_id == campaign_id))
    await db.execute(delete(OptimizationPlan).where(OptimizationPlan.campaign_id == campaign_id))
    await db.execute(delete(PerformanceAnalysis).where(PerformanceAnalysis.campaign_id == campaign_id))
    await db.execute(delete(ImportedFieldProvenance).where(ImportedFieldProvenance.entity_id == campaign_id))

    # Campaign contents and snapshots
    c_stmt = select(CampaignContent.id).where(CampaignContent.campaign_id == campaign_id)
    c_res = await db.execute(c_stmt)
    content_ids = c_res.scalars().all()
    if content_ids:
        await db.execute(
            delete(ContentPerformanceSnapshot).where(
                ContentPerformanceSnapshot.campaign_content_id.in_(content_ids)
            )
        )
    await db.execute(delete(CampaignContent).where(CampaignContent.campaign_id == campaign_id))

    # Campaign-creator relationships (join table only; shared creator records in influencers table remain untouched)
    await db.execute(delete(CampaignInfluencer).where(CampaignInfluencer.campaign_id == campaign_id))
    await db.execute(delete(CampaignStrategy).where(CampaignStrategy.campaign_id == campaign_id))
    await db.execute(delete(AgentRun).where(AgentRun.campaign_id == campaign_id))

    # Record user activity before deleting campaign
    activity = CampaignActivity(
        id=f"act-{uuid.uuid4().hex[:8]}",
        user_id=current_user.id,
        campaign_id=None,
        activity_type="CAMPAIGN_DELETED",
        title=f"Campaign '{camp_name}' deleted",
        description=f"Campaign '{camp_name}' (ID: {campaign_id}) was permanently removed.",
        metadata_json={"deleted_campaign_id": campaign_id, "deleted_campaign_name": camp_name},
    )
    db.add(activity)

    await db.delete(campaign)
    await db.commit()


@router.get(
    "/{campaign_id}/activities",
    response_model=List[CampaignActivityResponse],
    summary="Get activities for a campaign",
)
async def get_campaign_activities(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify campaign belongs to current user
    camp_stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    camp_res = await db.execute(camp_stmt)
    if not camp_res.scalar_one_or_none():
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    stmt = (
        select(CampaignActivity)
        .where(
            CampaignActivity.campaign_id == campaign_id,
            CampaignActivity.user_id == current_user.id,
        )
        .order_by(CampaignActivity.created_at.desc())
    )
    result = await db.execute(stmt)
    activities = result.scalars().all()
    return [CampaignActivityResponse.model_validate(a) for a in activities]


@router.post(
    "/{campaign_id}/fetch-influencers",
    response_model=InfluencerFetchResponse,
    summary="Deprecated: use POST /campaigns/{campaign_id}/discover-creators",
    deprecated=True,
)
async def fetch_campaign_influencers(
    campaign_id: str,
    payload: Optional[InfluencerFetchRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Legacy alias kept so older clients keep working.

    Runs the same campaign-scoped discovery pipeline and reports results in the
    previous response shape.
    """
    camp_stmt = select(Campaign).where(
        Campaign.id == campaign_id,
        Campaign.owner_id == current_user.id,
    )
    camp_res = await db.execute(camp_stmt)
    campaign = camp_res.scalar_one_or_none()
    if not campaign:
        raise NotFoundException(detail=f"Campaign {campaign_id} not found")

    service = CreatorDiscoveryService()
    res = await discover_for_campaign_with_retry(
        db=db,
        service=service,
        campaign=campaign,
        user_id=current_user.id,
        limit=payload.limit if payload and payload.limit else 25,
        force_refresh=payload.force_refresh if payload else False,
    )
    await db.commit()

    stats = res.get("stats", {})
    links = res.get("links", [])

    # Only the creators linked to this campaign, never the whole influencer table.
    inf_res = await db.execute(
        select(Influencer)
        .join(CampaignInfluencer, CampaignInfluencer.influencer_id == Influencer.id)
        .where(CampaignInfluencer.campaign_id == campaign.id)
    )
    campaign_influencers = inf_res.scalars().all()

    return InfluencerFetchResponse(
        campaign_id=campaign.id,
        status=res.get("status", "completed"),
        total_discovered=len(links),
        providers={
            "youtube": ProviderResultSchema(
                status="success" if res.get("status") == "completed" else "empty",
                fetched=stats.get("passed_filters", 0),
                created=stats.get("created", 0),
                updated=stats.get("updated", 0),
            )
        },
        influencers=[InfluencerResponse.model_validate(i) for i in campaign_influencers],
    )
