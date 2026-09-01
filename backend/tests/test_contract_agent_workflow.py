"""Comprehensive test suite for Contract Agent workflow, readiness, verification, and human approval."""

import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.contract import ContractAgent, ContractAgentOutput
from app.ai.agents.supervisor import SupervisorAgent
from app.ai.schemas import AgentResultEnvelope
from app.ai.workflow_states import AgentRunStatus, WorkflowState
from app.core.exceptions import AgentValidationException
from app.core.security import create_access_token
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.contract import Contract
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage
from app.models.user import User
from app.services.contract_readiness_service import ContractReadinessService


@pytest.mark.asyncio
async def test_contract_readiness_locked_when_awaiting_reply(db_session: AsyncSession):
    """Test 38: Outreach not completed (AWAITING_REPLY / READY) -> Contract = LOCKED."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Beauty Fest",
        brand="GlowBrand",
        budget=100000.0,
        objective="Awareness",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_PENDING,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-{uuid.uuid4().hex[:6]}",
        name="Beauty Influencer",
        username="beauty_inf",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.CONTACTED,
    )
    db_session.add(link)

    msg = OutreachMessage(
        id=f"outr-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        body="Initial pitch",
        status="SENT",
        response_status="PENDING_RESPONSE",
    )
    db_session.add(msg)
    await db_session.commit()

    service = ContractReadinessService(db_session)
    res = await service.check_readiness(campaign_id=campaign.id, influencer_id=inf.id, user=user)

    assert res.ready is False
    assert res.status == "LOCKED"
    assert "accepted" in res.blocking_reason.lower()

    # ContractAgent must also refuse execution
    agent = ContractAgent()
    from app.ai.agents.base import AgentContext
    ctx = AgentContext(db=db_session, campaign=campaign, user=user, extras={"influencer_id": inf.id})
    with pytest.raises(AgentValidationException) as excinfo:
        await agent.build_context(ctx)
    assert "CONTRACT_GATE" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_contract_readiness_locked_when_negotiating(db_session: AsyncSession):
    """Test 39: Status = NEGOTIATING -> Contract = LOCKED / WAITING."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Fashion Week",
        brand="StyleHub",
        budget=120000.0,
        objective="Conversions",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_PENDING,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-{uuid.uuid4().hex[:6]}",
        name="Fashion Icon",
        username="fashion_icon",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.NEGOTIATING,
    )
    db_session.add(link)
    await db_session.commit()

    service = ContractReadinessService(db_session)
    res = await service.check_readiness(campaign_id=campaign.id, influencer_id=inf.id, user=user)

    assert res.ready is False
    assert res.status == "LOCKED"
    assert "negotiation" in res.blocking_reason.lower()


@pytest.mark.asyncio
async def test_contract_readiness_not_applicable_when_declined(db_session: AsyncSession):
    """Test 40: Status = DECLINED -> Contract = NOT_APPLICABLE."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Gaming Showcase",
        brand="GameZone",
        budget=80000.0,
        objective="Engagement",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_PENDING,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-{uuid.uuid4().hex[:6]}",
        name="Gamer Streamer",
        username="gamer_streamer",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.DECLINED,
    )
    db_session.add(link)
    await db_session.commit()

    service = ContractReadinessService(db_session)
    res = await service.check_readiness(campaign_id=campaign.id, influencer_id=inf.id, user=user)

    assert res.ready is False
    assert res.status == "NOT_APPLICABLE"
    assert "declined" in res.blocking_reason.lower()


@pytest.mark.asyncio
async def test_contract_readiness_ready_when_accepted_with_terms(db_session: AsyncSession):
    """Test 41: Status = ACCEPTED, user confirmation = True, rate & deliverables exist -> Contract = READY."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Fitness App Launch",
        brand="FitLife",
        budget=200000.0,
        objective="App Installs",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-{uuid.uuid4().hex[:6]}",
        name="Fitness Coach",
        username="fit_coach",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.ACCEPTED,
    )
    db_session.add(link)

    msg = OutreachMessage(
        id=f"outr-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        body="Collaboration offer",
        status="ACCEPTED",
        response_status="ACCEPTED",
        final_amount=55000.0,
        currency="INR",
        deliverables=["1 YouTube Video", "1 YouTube Short"],
        timeline_start="2026-09-01",
        timeline_end="2026-09-15",
    )
    db_session.add(msg)
    await db_session.commit()

    service = ContractReadinessService(db_session)
    res = await service.check_readiness(campaign_id=campaign.id, influencer_id=inf.id, user=user)

    assert res.ready is True
    assert res.status == "READY"
    assert res.missing_fields == []
    assert res.final_terms["agreed_rate"] == 55000.0
    assert res.final_terms["deliverables"] == ["1 YouTube Video", "1 YouTube Short"]


@pytest.mark.asyncio
async def test_contract_readiness_missing_terms(db_session: AsyncSession):
    """Test 42: Status = ACCEPTED, but rate is missing -> CONTRACT_INFORMATION_REQUIRED (do not invent rate)."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Cooking Masterclass",
        brand="ChefPro",
        budget=50000.0,
        objective="Sales",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-{uuid.uuid4().hex[:6]}",
        name="Chef Maria",
        username="chef_maria",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.ACCEPTED,
    )
    db_session.add(link)

    msg = OutreachMessage(
        id=f"outr-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        body="Collaboration offer",
        status="ACCEPTED",
        response_status="ACCEPTED",
        final_amount=None,  # Missing rate!
        deliverables=[],  # Missing deliverables!
    )
    db_session.add(msg)
    await db_session.commit()

    service = ContractReadinessService(db_session)
    res = await service.check_readiness(campaign_id=campaign.id, influencer_id=inf.id, user=user)

    assert res.ready is False
    assert res.status == "CONTRACT_INFORMATION_REQUIRED"
    assert "agreed_rate" in res.missing_fields
    assert "deliverables" in res.missing_fields


@pytest.mark.asyncio
async def test_contract_comparison_compensation_mismatch(db_session: AsyncSession):
    """Test 43: Negotiated: ₹55,000, Contract document says ₹65,000 -> Flag COMPENSATION_MISMATCH, severity HIGH."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Smart Tech Launch",
        brand="TechStar",
        budget=100000.0,
        objective="Traffic",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-{uuid.uuid4().hex[:6]}",
        name="Tech Guy",
        username="tech_guy",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.ACCEPTED,
    )
    db_session.add(link)

    msg = OutreachMessage(
        id=f"outr-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        body="Collaboration offer",
        status="ACCEPTED",
        response_status="ACCEPTED",
        final_amount=55000.0,
        currency="INR",
        deliverables=["1 Dedicated Review Video"],
    )
    db_session.add(msg)
    await db_session.commit()

    agent = ContractAgent()
    from app.ai.agents.base import AgentContext
    ctx = AgentContext(
        db=db_session,
        campaign=campaign,
        user=user,
        extras={
            "influencer_id": inf.id,
            "contract_text": "AGREEMENT: The compensation for this engagement shall be INR 65,000 payable upon completion.",
        },
    )

    mock_analysis_output = ContractAgentOutput(
        contract_title="Influencer Collaboration Agreement",
        contract_summary="Contract contains compensation mismatch.",
        parties={"brand": "TechStar", "influencer": "Tech Guy"},
        commercial_terms={
            "agreed_rate": {
                "negotiated_value": 55000.0,
                "contract_value": 65000.0,
                "status": "MISMATCH",
            },
            "currency": "INR",
        },
        risk_flags=[{
            "severity": "HIGH",
            "issue": "COMPENSATION_MISMATCH",
            "reason": "Negotiated fee of INR 55,000 differs from contract stated INR 65,000.",
            "recommended_review": "Align compensation terms before approval.",
        }],
        overall_status="CRITICAL_ISSUES_FOUND",
        confidence=0.94,
    )

    with patch.object(
        agent,
        "call_llm",
        AsyncMock(
            return_value=AgentResultEnvelope(
                status="COMPLETED",
                summary="Mismatch detected",
                confidence=0.94,
                recommendations=[mock_analysis_output.model_dump()],
                data=mock_analysis_output.model_dump(),
                provider="groq",
                model="llama-3.3-70b-versatile",
                provider_latency_ms=90,
                grok_called=True,
            )
        ),
    ):
        result = await agent.execute(ctx)
        assert result.data["overall_status"] == "CRITICAL_ISSUES_FOUND"
        flags = result.data["risk_flags"]
        assert any(f["issue"] == "COMPENSATION_MISMATCH" and f["severity"] == "HIGH" for f in flags)
        # Commercial term protection ensures the database authoritative rate is preserved as 55,000
        assert result.data["agreed_value"] == 55000.0


@pytest.mark.asyncio
async def test_groq_failure_sets_failed_state_no_fake_fallback(db_session: AsyncSession):
    """Test 46: Invalid Groq configuration or failure -> AgentRun = FAILED, no fake analysis."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Auto Test Campaign",
        brand="AutoBrand",
        budget=100000.0,
        objective="Testing",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-{uuid.uuid4().hex[:6]}",
        name="Test Creator",
        username="test_creator",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.ACCEPTED,
    )
    db_session.add(link)

    msg = OutreachMessage(
        id=f"outr-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        body="Collaboration offer",
        status="ACCEPTED",
        response_status="ACCEPTED",
        final_amount=50000.0,
        currency="INR",
        deliverables=["1 Dedicated Video"],
    )
    db_session.add(msg)
    await db_session.commit()

    supervisor = SupervisorAgent(db_session)

    # Simulate provider failure (e.g. Groq API error)
    from app.core.exceptions import AIProviderException
    with patch.object(ContractAgent, "call_llm", AsyncMock(side_effect=AIProviderException(detail="Groq API 503 Service Unavailable"))):
        res = await supervisor.run_contract(
            campaign=campaign,
            user=user,
            influencer_id=inf.id,
            trigger="manual",
        )

        assert res["agent_run"].status == AgentRunStatus.FAILED
        assert "Groq API 503" in res["agent_run"].error_message
        assert res["contract"] is None  # No fake contract analysis synthesized!


@pytest.mark.asyncio
async def test_user_tenant_isolation_on_contracts(client: AsyncClient, db_session: AsyncSession):
    """Test 47: User A's contract must never be accessible to User B."""
    user_a = User(id=uuid.uuid4(), email=f"user_a_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User A")
    user_b = User(id=uuid.uuid4(), email=f"user_b_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User B")
    db_session.add_all([user_a, user_b])

    camp_a = Campaign(
        id=f"camp-a-{uuid.uuid4().hex[:6]}",
        owner_id=user_a.id,
        name="User A Campaign",
        brand="Brand A",
        budget=100000.0,
        objective="Sales",
        start_date="2026-09-01",
        end_date="2026-09-30",
    )
    db_session.add(camp_a)

    contract_a = Contract(
        id=f"cntr-a-{uuid.uuid4().hex[:6]}",
        campaign_id=camp_a.id,
        influencer_id="inf-a-1",
        creator="Creator A",
        username="creator_a",
        campaign=camp_a.name,
        value=50000.0,
        currency="INR",
        status="pending_signature",
        start_date="2026-09-01",
        end_date="2026-09-30",
        payment_due="Net 30",
        risk="low",
        deliverables=["1 Video"],
        usage_rights="12 months",
        exclusivity="None",
    )
    db_session.add(contract_a)
    await db_session.commit()

    token_b = create_access_token(subject=str(user_b.id))
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B tries to get User A's contract
    res = await client.get(f"/api/v1/contracts/{contract_a.id}", headers=headers_b)
    assert res.status_code == 404

    # User B lists contracts -> User A's contract is not in the list
    list_res = await client.get("/api/v1/contracts", headers=headers_b)
    assert list_res.status_code == 200
    contracts_b = list_res.json()
    assert all(c["id"] != contract_a.id for c in contracts_b)


@pytest.mark.asyncio
async def test_human_contract_approval_and_change_request_lifecycle(client: AsyncClient, db_session: AsyncSession):
    """Test human approval, request changes, and supervisor state notification."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-appr-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Product Launch",
        brand="BrandCo",
        budget=100000.0,
        objective="Conversions",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-appr-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-appr-{uuid.uuid4().hex[:6]}",
        name="Star Creator",
        username="star_creator",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.ACCEPTED,
    )
    db_session.add(link)

    contract = Contract(
        id=f"cntr-appr-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        creator=inf.name,
        username=inf.username,
        campaign=campaign.name,
        value=60000.0,
        currency="INR",
        status="pending_signature",
        version=1,
        start_date="2026-09-01",
        end_date="2026-09-30",
        payment_due="Net 30",
        risk="low",
        deliverables=["1 Dedicated Video"],
        usage_rights="12 months digital",
        exclusivity="Non-exclusive",
    )
    db_session.add(contract)
    await db_session.commit()

    token = create_access_token(subject=str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Request Changes
    change_payload = {
        "requested_changes": "Increase exclusivity window to 60 days post launch.",
        "reason": "Brand category protection required.",
    }
    res_chg = await client.post(f"/api/v1/contracts/{contract.id}/request-changes", json=change_payload, headers=headers)
    assert res_chg.status_code == 200
    data_chg = res_chg.json()
    assert data_chg["status"] == "CHANGES_REQUESTED"
    assert data_chg["version"] == 2
    change_reqs = data_chg.get("change_requests") or data_chg.get("changeRequests")
    assert len(change_reqs) == 1

    # 2. Approve Contract
    res_appr = await client.post(f"/api/v1/contracts/{contract.id}/approve", json={"notes": "Final terms verified."}, headers=headers)
    assert res_appr.status_code == 200
    data_appr = res_appr.json()
    assert data_appr["status"] == "APPROVED"
    assert (data_appr.get("approvedBy") or data_appr.get("approved_by")) == str(user.id)
    assert (data_appr.get("approvedAt") or data_appr.get("approved_at")) is not None

    # Verify Campaign workflow advanced to CONTRACT_COMPLETED
    await db_session.refresh(campaign)
    assert campaign.workflow_state == WorkflowState.CONTRACT_COMPLETED


@pytest.mark.asyncio
async def test_deterministic_payment_math_and_suggested_terms(db_session: AsyncSession):
    """Verify deterministic payment percentage and amount reconciliation."""
    from app.schemas.contract import ContractTermsPayload, CompensationTerms, PaymentScheduleTerms, TimelineTerms

    # 1. 50/50 test
    payload_5050 = ContractTermsPayload(
        compensation=CompensationTerms(total=50000.0, currency="INR"),
        payment=PaymentScheduleTerms(structure="50_50"),
        deliverables=["1 Dedicated Video", "2 Shorts"],
    )
    assert payload_5050.payment.advance_amount == 25000.0
    assert payload_5050.payment.balance_amount == 25000.0
    assert payload_5050.payment.advance_amount + payload_5050.payment.balance_amount == 50000.0
    assert "25,000.00" in payload_5050.payment.terms_text

    # 2. Custom 30/70 split
    payload_custom = ContractTermsPayload(
        compensation=CompensationTerms(total=100000.0, currency="INR"),
        payment=PaymentScheduleTerms(structure="custom", advance_percentage=30.0),
        deliverables=["1 Dedicated Video"],
    )
    assert payload_custom.payment.advance_amount == 30000.0
    assert payload_custom.payment.balance_amount == 70000.0
    assert payload_custom.payment.advance_percentage == 30.0
    assert payload_custom.payment.balance_percentage == 70.0


@pytest.mark.asyncio
async def test_contract_agent_synthesizes_complete_contract_with_zero_placeholders(db_session: AsyncSession):
    """Verify Contract Agent outputs zero generic bracketed placeholders."""
    user = User(id=uuid.uuid4(), email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Skincare Glow",
        brand="GlowNaturals",
        budget=100000.0,
        objective="Sales",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-{uuid.uuid4().hex[:6]}",
        name="Parul Garg",
        username="makeupbyparulgarg",
        platform="youtube",
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.ACCEPTED,
    )
    db_session.add(link)

    msg = OutreachMessage(
        id=f"outr-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        body="Collaboration terms",
        status="ACCEPTED",
        response_status="ACCEPTED",
        final_amount=50000.0,
        currency="INR",
        deliverables=["1 Dedicated collaboration video"],
        timeline_start="2026-09-05",
        timeline_end="2026-09-25",
    )
    db_session.add(msg)
    await db_session.commit()

    agent = ContractAgent()
    from app.ai.agents.base import AgentContext

    confirmed_terms = {
        "compensation": {"total": 50000.0, "currency": "INR"},
        "payment": {
            "structure": "50_50",
            "advance_percentage": 50.0,
            "advance_amount": 25000.0,
            "balance_percentage": 50.0,
            "balance_amount": 25000.0,
            "method": "Bank Transfer",
            "balance_due_days": 7,
            "terms_text": "INR 25,000.00 advance upon execution; INR 25,000.00 via Bank Transfer within 7 days of completion.",
        },
        "deliverables": ["1 Dedicated collaboration video"],
        "timeline": {"start_date": "2026-09-05", "end_date": "2026-09-25"},
        "revisions": {"allowed_rounds": 2, "scope": "Factual accuracy and brand guidelines."},
        "approval": {"pre_publication_required": True},
        "product_claims": {"policy": "BRAND_APPROVED_ONLY"},
        "usage_rights": {"organic_reposting": True, "paid_ads": False, "duration": "3 Months", "territory": "India"},
        "ownership": {"copyright_owner": "INFLUENCER"},
        "exclusivity": {"required": True, "category": "Skincare serums", "duration_days": 30},
    }

    ctx = AgentContext(
        db=db_session,
        campaign=campaign,
        user=user,
        extras={"influencer_id": inf.id, "confirmed_terms": confirmed_terms},
    )

    context_payload = await agent.build_context(ctx)
    assert context_payload["confirmed_terms"]["compensation"]["total"] == 50000.0
    assert context_payload["confirmed_terms"]["payment"]["advance_amount"] == 25000.0

    mock_llm_response = ContractAgentOutput(
        contract_title="Influencer Collaboration Agreement",
        contract_summary="Complete agreement for Parul Garg",
        parties={"brand": "GlowNaturals", "influencer": "Parul Garg"},
        contract_body=(
            "INFLUENCER COLLABORATION AGREEMENT\n\n"
            "This Agreement is between GlowNaturals ('Brand') and Parul Garg (@makeupbyparulgarg) ('Creator').\n"
            "1. Deliverables: 1 Dedicated collaboration video.\n"
            "2. Compensation: INR 50,000.00 total. Advance of INR 25,000.00 payable upon execution; balance of INR 25,000.00 payable within 7 days post completion via Bank Transfer.\n"
            "3. Timeline: Active from 2026-09-05 to 2026-09-25.\n"
            "4. Revisions: Up to 2 rounds for factual accuracy.\n"
            "5. Usage Rights: 3 Months organic social media usage in India.\n"
            "6. Exclusivity: Direct competitor exclusivity in Skincare serums for 30 days.\n"
            "7. Product Claims: Only brand-approved claims permitted.\n"
            "8. Signatures: Signed on behalf of GlowNaturals and Parul Garg."
        ),
        overall_status="READY_FOR_REVIEW",
    )

    with patch.object(agent.llm, "generate_structured_with_meta", new_callable=AsyncMock) as mock_gen:
        from app.ai.schemas import LLMRawResponse
        meta = LLMRawResponse(provider="groq", model="llama-3.3-70b-versatile", latency_ms=120.0, raw_text="{}", content="{}")
        mock_gen.return_value = (mock_llm_response, meta)

        res = await agent.call_llm(ctx, "", "", context_payload)
        assert res.status == "COMPLETED"
        body = res.data["contract_body"]
        
        # Test 44: No generic placeholders in valid generated contract
        for forbidden in ["[Insert", "[Enter", "[Specify", "[Add", "TBD", "Lorem Ipsum"]:
            assert forbidden.lower() not in body.lower(), f"Found forbidden placeholder '{forbidden}' in contract body"

