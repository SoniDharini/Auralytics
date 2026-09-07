"""Campaign workflow guidance is derived from existing records, not frontend state."""

from datetime import datetime, timezone
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_execution import AgentRun
from app.models.approval import Approval
from app.models.campaign_content import CampaignContent, ContentType, TrackingStatus
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.campaign_strategy import CampaignStrategy
from app.models.contract import Contract
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage


async def _auth(client: AsyncClient, email: str):
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Workflow Tester",
            "email": email,
            "password": "securePassword456",
            "company_name": "GlowNaturals",
        },
    )
    assert res.status_code == 201
    body = res.json()
    return {
        "Authorization": f"Bearer {body['access_token']}",
        "user_id": body["user"]["id"],
    }


async def _create_campaign(client: AsyncClient, headers: dict) -> str:
    res = await client.post(
        "/api/v1/campaigns",
        json={
            "name": "GlowUp Summer Campaign",
            "brand": "GlowNaturals",
            "budget": 200000,
            "objective": "Product Launch",
            "start_date": "2026-09-01",
            "end_date": "2026-10-15",
            "status": "planning",
            "health": "healthy",
        },
        headers=headers,
    )
    assert res.status_code == 201
    return res.json()["id"]


async def _get_workflow(client: AsyncClient, headers: dict, campaign_id: str):
    res = await client.get(f"/api/v1/campaigns/{campaign_id}/workflow", headers=headers)
    assert res.status_code == 200
    return res.json()


def _step(body: dict, key: str) -> dict:
    return next(s for s in body["steps"] if s["key"] == key)


@pytest.mark.asyncio
async def test_new_campaign_next_step_is_generate_strategy(client: AsyncClient):
    headers = await _auth(client, "wf.new@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    body = await _get_workflow(client, headers, camp_id)

    assert body["current_step"] == "STRATEGY"
    assert body["next_step"] == "GENERATE_STRATEGY"
    assert body["next_action"]["label"] == "Generate AI Strategy"
    assert body["next_action"]["enabled"] is True
    assert _step(body, "CAMPAIGN_CREATED")["status"] == "COMPLETED"
    assert _step(body, "STRATEGY")["status"] == "NEXT"
    assert _step(body, "DISCOVERY")["status"] == "LOCKED"
    assert _step(body, "DISCOVERY")["hint"] == "Complete AI Strategy first."


@pytest.mark.asyncio
async def test_strategy_completed_next_step_is_discover(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.strategy@glownaturals.com")
    camp_id = await _create_campaign(client, headers)

    db_session.add(
        CampaignStrategy(
            campaign_id=camp_id,
            strategy_json={"objective": "awareness", "discovery_priorities": ["skincare"]},
            version=1,
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["next_step"] == "DISCOVER_INFLUENCERS"
    assert _step(body, "STRATEGY")["status"] == "COMPLETED"
    assert _step(body, "DISCOVERY")["status"] == "NEXT"
    assert _step(body, "SHORTLIST")["status"] == "LOCKED"


@pytest.mark.asyncio
async def test_discovery_completed_next_step_is_shortlist(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.discover@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(
        CampaignStrategy(
            campaign_id=camp_id, strategy_json={"ok": True}, version=1
        )
    )
    inf = Influencer(
        id="inf-wf-1",
        platform="youtube",
        external_id="ext-wf-1",
        username="skincare_creator",
        name="Skincare Creator",
    )
    db_session.add(inf)
    db_session.add(
        CampaignInfluencer(
            id="cinf-wf-1",
            campaign_id=camp_id,
            influencer_id="inf-wf-1",
            status=CampaignInfluencerStatus.DISCOVERED,
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["next_step"] == "SHORTLIST_INFLUENCERS"
    assert body["discovered_count"] == 1
    assert _step(body, "DISCOVERY")["status"] == "COMPLETED"
    assert _step(body, "SHORTLIST")["status"] == "NEXT"


@pytest.mark.asyncio
async def test_shortlist_next_step_is_approve(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.shortlist@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Influencer(
            id="inf-wf-2",
            platform="youtube",
            external_id="ext-wf-2",
            username="creator_two",
            name="Creator Two",
        )
    )
    db_session.add(
        CampaignInfluencer(
            id="cinf-wf-2",
            campaign_id=camp_id,
            influencer_id="inf-wf-2",
            status=CampaignInfluencerStatus.SHORTLISTED,
        )
    )
    db_session.add(
        Approval(
            id="appr-wf-1",
            agent="Discovery Agent",
            type="shortlist",
            action="Approve shortlist",
            reason="Ranked creators ready",
            campaign="GlowUp Summer Campaign",
            financial_impact="None",
            confidence=0.8,
            timestamp="now",
            status="pending",
            user_id=UUID(headers["user_id"]),
            campaign_id=camp_id,
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["next_step"] == "APPROVE_SHORTLIST"
    assert body["pending_approval"] is True
    assert _step(body, "SHORTLIST")["status"] == "COMPLETED"
    assert _step(body, "APPROVAL")["status"] == "WAITING_APPROVAL"


@pytest.mark.asyncio
async def test_approved_shortlist_next_step_is_generate_outreach(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.approve@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Influencer(
            id="inf-wf-3",
            platform="youtube",
            external_id="ext-wf-3",
            username="creator_three",
            name="Creator Three",
        )
    )
    db_session.add(
        CampaignInfluencer(
            id="cinf-wf-3",
            campaign_id=camp_id,
            influencer_id="inf-wf-3",
            status=CampaignInfluencerStatus.SHORTLISTED,
        )
    )
    db_session.add(
        Approval(
            id="appr-wf-2",
            agent="Discovery Agent",
            type="shortlist",
            action="Approve shortlist",
            reason="Approved",
            campaign="GlowUp Summer Campaign",
            financial_impact="None",
            confidence=0.9,
            timestamp="now",
            status="approve",
            user_id=UUID(headers["user_id"]),
            campaign_id=camp_id,
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["next_step"] == "GENERATE_OUTREACH"
    assert "Generate Outreach" in body["next_action"]["label"]
    assert _step(body, "APPROVAL")["status"] == "COMPLETED"
    assert _step(body, "OUTREACH")["status"] == "NEXT"


@pytest.mark.asyncio
async def test_outreach_generated_next_step_is_review(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.outreach@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Influencer(
            id="inf-wf-4",
            platform="youtube",
            external_id="ext-wf-4",
            username="creator_four",
            name="Creator Four",
        )
    )
    db_session.add(
        CampaignInfluencer(
            id="cinf-wf-4",
            campaign_id=camp_id,
            influencer_id="inf-wf-4",
            status=CampaignInfluencerStatus.SHORTLISTED,
        )
    )
    db_session.add(
        OutreachMessage(
            id="outr-wf-1",
            campaign_id=camp_id,
            influencer_id="inf-wf-4",
            influencer_name="Creator Four",
            influencer_username="creator_four",
            campaign_name="GlowUp Summer Campaign",
            body="Hi, we'd love to collaborate.",
            status="READY",
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["next_step"] == "REVIEW_OUTREACH"
    assert body["next_action"]["label"] == "Review Outreach"
    assert _step(body, "OUTREACH")["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_failed_strategy_stays_on_retry_not_discovery(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.fail@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(
        AgentRun(
            user_id=UUID(headers["user_id"]),
            campaign_id=camp_id,
            agent_name="strategy",
            status="FAILED",
            error_message="GROQ_API_KEY is missing",
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["next_step"] == "GENERATE_STRATEGY"
    assert body["next_action"]["label"] == "Retry Strategy"
    assert _step(body, "STRATEGY")["status"] == "FAILED"
    assert _step(body, "DISCOVERY")["status"] == "LOCKED"


@pytest.mark.asyncio
async def test_failed_discovery_without_creators_does_not_hide_strategy(
    client: AsyncClient, db_session: AsyncSession
):
    """Strategy saved + discovery agent failed (no YouTube candidates) → next is Discover, not Retry Strategy."""
    headers = await _auth(client, "wf.discfail@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        AgentRun(
            user_id=UUID(headers["user_id"]),
            campaign_id=camp_id,
            agent_name="discovery",
            status="FAILED",
            error_message="No influencer candidates found for this campaign. Run creator discovery first.",
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["next_step"] == "DISCOVER_INFLUENCERS"
    assert body["next_action"]["label"] == "Discover Influencers"
    assert _step(body, "STRATEGY")["status"] == "COMPLETED"
    assert _step(body, "DISCOVERY")["status"] == "NEXT"


@pytest.mark.asyncio
async def test_youtube_creators_exist_despite_failed_ranking_unlocks_shortlist(
    client: AsyncClient, db_session: AsyncSession
):
    """Real YouTube creators are discovery success even if Grok ranking later failed."""
    headers = await _auth(client, "wf.rankfail@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Influencer(
            id="inf-wf-rankfail",
            platform="youtube",
            external_id="ext-wf-rankfail",
            username="rankfail_creator",
            name="Rank Fail Creator",
        )
    )
    db_session.add(
        CampaignInfluencer(
            id="cinf-wf-rankfail",
            campaign_id=camp_id,
            influencer_id="inf-wf-rankfail",
            status=CampaignInfluencerStatus.DISCOVERED,
        )
    )
    db_session.add(
        AgentRun(
            user_id=UUID(headers["user_id"]),
            campaign_id=camp_id,
            agent_name="discovery",
            status="FAILED",
            error_message="Groq ranking timed out",
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["next_step"] == "SHORTLIST_INFLUENCERS"
    assert body["discovered_count"] == 1
    assert body["next_action"]["label"] == "Review Influencers"
    assert _step(body, "DISCOVERY")["status"] == "COMPLETED"
    assert _step(body, "SHORTLIST")["status"] == "NEXT"


@pytest.mark.asyncio
async def test_workflow_is_isolated_between_users(client: AsyncClient):
    headers_a = await _auth(client, "wf.owner@glownaturals.com")
    camp_id = await _create_campaign(client, headers_a)

    headers_b = await _auth(client, "wf.intruder@glownaturals.com")
    res = await client.get(f"/api/v1/campaigns/{camp_id}/workflow", headers=headers_b)
    assert res.status_code == 404

    own = await client.get(f"/api/v1/campaigns/{camp_id}/workflow", headers=headers_a)
    assert own.status_code == 200


@pytest.mark.asyncio
async def test_accepted_creator_advances_to_contract_step(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.contract1@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Influencer(
            id="inf-wf-c1",
            platform="youtube",
            external_id="ext-wf-c1",
            username="contract_creator",
            name="Contract Creator",
        )
    )
    db_session.add(
        CampaignInfluencer(
            id="cinf-wf-c1",
            campaign_id=camp_id,
            influencer_id="inf-wf-c1",
            status=CampaignInfluencerStatus.ACCEPTED,
        )
    )
    db_session.add(
        OutreachMessage(
            id="outr-wf-c1",
            campaign_id=camp_id,
            influencer_id="inf-wf-c1",
            influencer_name="Contract Creator",
            influencer_username="contract_creator",
            campaign_name="GlowUp Summer Campaign",
            body="Agreed terms",
            status="ACCEPTED",
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["current_step"] == "CONTRACT"
    assert body["next_step"] == "CONTRACT"
    assert body["next_action"]["label"] == "Generate Contract"
    assert _step(body, "OUTREACH")["status"] == "COMPLETED"
    assert _step(body, "CONTRACT")["status"] == "NEXT"


@pytest.mark.asyncio
async def test_pending_contract_is_waiting_approval(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.contract2@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Contract(
            id="cont-wf-1",
            campaign_id=camp_id,
            influencer_id="inf-wf-c2",
            creator="Contract Creator",
            username="contract_creator",
            campaign="GlowUp Summer Campaign",
            value=50000.0,
            currency="INR",
            status="pending_signature",
            version=1,
            start_date="2026-09-01",
            end_date="2026-10-01",
            payment_due="Net 30",
            risk="low",
            deliverables=["1 Dedicated Video"],
            usage_rights="Digital rights",
            exclusivity="Category exclusive",
            overall_status="READY_FOR_REVIEW",
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["current_step"] == "CONTRACT"
    assert _step(body, "CONTRACT")["status"] == "WAITING_APPROVAL"


@pytest.mark.asyncio
async def test_approved_contract_advances_to_performance_step(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.perf1@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Contract(
            id="cont-wf-approved",
            campaign_id=camp_id,
            influencer_id="inf-wf-c3",
            creator="Contract Creator",
            username="contract_creator",
            campaign="GlowUp Summer Campaign",
            value=50000.0,
            currency="INR",
            status="APPROVED",
            version=1,
            start_date="2026-09-01",
            end_date="2026-10-01",
            payment_due="Net 30",
            risk="low",
            deliverables=["1 Dedicated Video"],
            usage_rights="Digital rights",
            exclusivity="Category exclusive",
            overall_status="APPROVED",
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["current_step"] == "PERFORMANCE"
    assert body["next_step"] == "TRACK_PERFORMANCE"
    assert _step(body, "CONTRACT")["status"] == "COMPLETED"
    assert _step(body, "PERFORMANCE")["status"] == "NEXT"


@pytest.mark.asyncio
async def test_tracked_content_advances_to_analyze_performance(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.perf2@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Contract(
            id="cont-wf-approved-2",
            campaign_id=camp_id,
            influencer_id="inf-wf-c4",
            creator="Creator Four",
            username="creator_four",
            campaign="GlowUp Summer Campaign",
            value=50000.0,
            currency="INR",
            status="signed",
            version=1,
            start_date="2026-09-01",
            end_date="2026-10-01",
            payment_due="Net 30",
            risk="low",
            deliverables=["1 Dedicated Video"],
            usage_rights="Digital rights",
            exclusivity="Category exclusive",
            overall_status="APPROVED",
        )
    )
    db_session.add(
        CampaignContent(
            id="content-wf-1",
            campaign_id=camp_id,
            influencer_id="inf-wf-c4",
            content_type=ContentType.YOUTUBE_VIDEO,
            external_content_id="dQw4w9WgXcQ",
            content_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
            tracking_status=TrackingStatus.TRACKING,
            current_views=15000,
            agreed_cost=50000.0,
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["current_step"] == "PERFORMANCE"
    assert body["next_step"] == "ANALYZE_PERFORMANCE"
    assert "Analyze Performance" in body["next_action"]["label"]


@pytest.mark.asyncio
async def test_completed_performance_advances_to_optimization(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.opt1@glownaturals.com")
    camp_id = await _create_campaign(client, headers)
    user_id = UUID(headers["user_id"])
    db_session.add(CampaignStrategy(campaign_id=camp_id, strategy_json={"ok": True}, version=1))
    db_session.add(
        Contract(
            id="cont-wf-approved-3",
            campaign_id=camp_id,
            influencer_id="inf-wf-c5",
            creator="Creator Five",
            username="creator_five",
            campaign="GlowUp Summer Campaign",
            value=50000.0,
            currency="INR",
            status="signed",
            version=1,
            start_date="2026-09-01",
            end_date="2026-10-01",
            payment_due="Net 30",
            risk="low",
            deliverables=["1 Dedicated Video"],
            usage_rights="Digital rights",
            exclusivity="Category exclusive",
            overall_status="APPROVED",
        )
    )
    db_session.add(
        CampaignContent(
            id="content-wf-2",
            campaign_id=camp_id,
            influencer_id="inf-wf-c5",
            content_type=ContentType.YOUTUBE_VIDEO,
            external_content_id="dQw4w9WgXcQ",
            content_url="https://youtube.com/watch?v=dQw4w9WgXcQ",
            tracking_status=TrackingStatus.TRACKING,
            current_views=25000,
            agreed_cost=50000.0,
        )
    )
    db_session.add(
        AgentRun(
            user_id=user_id,
            campaign_id=camp_id,
            agent_name="performance",
            status="COMPLETED",
            output_json={"kpis": {"views": 25000, "roas": 2.5}},
            completed_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    body = await _get_workflow(client, headers, camp_id)
    assert body["current_step"] == "OPTIMIZATION"
    assert body["next_step"] == "OPTIMIZE_CAMPAIGN"
    assert _step(body, "PERFORMANCE")["status"] == "COMPLETED"
    assert _step(body, "OPTIMIZATION")["status"] == "NEXT"


@pytest.mark.asyncio
async def test_approvals_endpoint_filters_by_campaign_id(
    client: AsyncClient, db_session: AsyncSession
):
    headers = await _auth(client, "wf.apprfilter@glownaturals.com")
    camp_a = await _create_campaign(client, headers)
    camp_b = await _create_campaign(client, headers)
    user_id = UUID(headers["user_id"])

    db_session.add(
        Approval(
            id="appr-filter-a",
            agent="Strategy Agent",
            type="campaign",
            action="Approve brief A",
            reason="Brief ready",
            campaign="Campaign A",
            financial_impact="None",
            confidence=0.9,
            timestamp="now",
            status="pending",
            user_id=user_id,
            campaign_id=camp_a,
        )
    )
    db_session.add(
        Approval(
            id="appr-filter-b",
            agent="Strategy Agent",
            type="campaign",
            action="Approve brief B",
            reason="Brief ready",
            campaign="Campaign B",
            financial_impact="None",
            confidence=0.9,
            timestamp="now",
            status="pending",
            user_id=user_id,
            campaign_id=camp_b,
        )
    )
    await db_session.commit()

    res_all = await client.get("/api/v1/approvals", headers=headers)
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    res_a = await client.get(f"/api/v1/approvals?campaign_id={camp_a}", headers=headers)
    assert res_a.status_code == 200
    assert len(res_a.json()) == 1
    assert res_a.json()[0]["id"] == "appr-filter-a"
