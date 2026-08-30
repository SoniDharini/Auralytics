import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.contract import ContractAgent, ContractAgentOutput
from app.ai.agents.outreach import ExtractedTerms, OutreachAgent, OutreachNegotiationOutput
from app.ai.agents.supervisor import SupervisorAgent
from app.ai.schemas import LLMRawResponse, AgentResultEnvelope
from app.ai.workflow_states import AgentRunStatus, WorkflowState
from app.core.exceptions import AgentValidationException
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.contract import Contract
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage
from app.models.user import User


@pytest.mark.asyncio
async def test_negotiation_output_term_extraction():
    """Verify numeric coercion and terms extraction in OutreachNegotiationOutput."""
    output = OutreachNegotiationOutput(
        conversation_state="NEGOTIATING_PRICE",
        influencer_reply_summary="Creator quoted ₹75,000 for 1 video.",
        extracted_terms=ExtractedTerms(
            creator_requested_price=75000,
            agreed_rate=None,
            deliverables=["1 dedicated YouTube video"],
        ),
        recommended_action="COUNTER_OFFER",
        message="Thank you. Would you consider ₹55,000?",
        short_dm="Would ₹55,000 work for 1 video?",
        confidence=0.92,
    )
    assert output.conversation_state == "NEGOTIATING_PRICE"
    assert output.extracted_terms.creator_requested_price == 75000.0
    assert output.extracted_terms.deliverables == ["1 dedicated YouTube video"]


@pytest.mark.asyncio
async def test_contract_agent_readiness_validation_rejects_unaccepted_creator(db_session: AsyncSession):
    """Verify ContractAgent raises validation error if creator is not ACCEPTED."""
    user_id = uuid.uuid4()
    user = User(id=user_id, email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id="camp-cntr-test",
        owner_id=user.id,
        name="Skincare Launch",
        brand="GlowSkin",
        budget=100000.0,
        objective="Drive awareness",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id="inf-cntr-1",
        external_id="yt-cntr-1",
        name="Skincare Guru",
        username="skincare_guru",
        platform="youtube",
        followers=80000,
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.NEGOTIATING,  # NOT ACCEPTED
    )
    db_session.add(link)
    await db_session.commit()

    agent = ContractAgent()
    from app.ai.agents.base import AgentContext
    ctx = AgentContext(db=db_session, campaign=campaign, user=user, extras={"influencer_id": inf.id})

    with pytest.raises(AgentValidationException) as excinfo:
        await agent.build_context(ctx)

    assert "CONTRACT_GATE" in str(excinfo.value.detail) or "ACCEPTED" in str(excinfo.value.detail)


@pytest.mark.asyncio
async def test_contract_agent_readiness_validation_rejects_missing_rate(db_session: AsyncSession):
    """Verify ContractAgent raises validation error if agreed rate is 0 or missing."""
    user_id = uuid.uuid4()
    user = User(id=user_id, email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id="camp-cntr-test2",
        owner_id=user.id,
        name="Skincare Launch",
        brand="GlowSkin",
        budget=100000.0,
        objective="Drive awareness",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id="inf-cntr-2",
        external_id="yt-cntr-2",
        name="Skincare Pro",
        username="skincare_pro",
        platform="youtube",
        followers=85000,
    )
    db_session.add(inf)

    link = CampaignInfluencer(
        id=f"ci-{uuid.uuid4().hex[:8]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.ACCEPTED,  # ACCEPTED but no rate provided
    )
    db_session.add(link)
    await db_session.commit()

    agent = ContractAgent()
    from app.ai.agents.base import AgentContext
    ctx = AgentContext(db=db_session, campaign=campaign, user=user, extras={"influencer_id": inf.id, "agreed_terms": {}})

    with pytest.raises(AgentValidationException) as excinfo:
        await agent.build_context(ctx)

    assert "CONTRACT_INFORMATION_REQUIRED" in str(excinfo.value.detail) or "rate" in str(excinfo.value.detail).lower()


@pytest.mark.asyncio
async def test_supervisor_run_negotiation_flow(db_session: AsyncSession):
    """Verify full supervisor negotiation flow updates history, state, and message."""
    user_id = uuid.uuid4()
    user = User(id=user_id, email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id="camp-neg-test",
        owner_id=user.id,
        name="Summer Campaign",
        brand="SummerBrand",
        budget=200000.0,
        objective="Conversions",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id="inf-neg-1",
        external_id="yt-neg-1",
        name="Creator Alex",
        username="alex_creates",
        platform="youtube",
        followers=95000,
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
        id="outr-neg-1",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        channel="EMAIL",
        subject="Collaboration Request",
        body="Initial pitch text",
        status="SENT",
    )
    db_session.add(msg)
    await db_session.commit()

    mock_negotiation_output = OutreachNegotiationOutput(
        conversation_state="NEGOTIATING_PRICE",
        influencer_reply_summary="Creator asked for ₹80,000",
        extracted_terms=ExtractedTerms(
            creator_requested_price=80000.0,
            agreed_rate=None,
            deliverables=["1 dedicated video"],
        ),
        recommended_action="COUNTER_OFFER",
        subject="Re: Collaboration Request",
        message="Thank you Alex. Our approved budget for this scope is ₹60,000. Would that work?",
        short_dm="Would ₹60,000 work for the dedicated video?",
        confidence=0.92,
    )
    mock_raw = LLMRawResponse(
        provider="groq",
        model="llama-3.3-70b-versatile",
        latency_ms=120,
        content="{}",
    )

    with patch.object(
        OutreachAgent,
        "call_llm",
        AsyncMock(
            return_value=AgentResultEnvelope(
                status="COMPLETED",
                summary="Generated follow-up counteroffer",
                confidence=0.92,
                recommendations=[mock_negotiation_output.model_dump()],
                data=mock_negotiation_output.model_dump(),
                provider=mock_raw.provider,
                model=mock_raw.model,
                provider_latency_ms=mock_raw.latency_ms,
                grok_called=True,
            )
        ),
    ):
        supervisor = SupervisorAgent(db_session)
        res = await supervisor.run_negotiation(
            campaign=campaign,
            user=user,
            outreach_message_id=msg.id,
            influencer_reply="My standard rate is ₹80,000 for a dedicated video.",
            user_instruction="Counter with ₹60,000",
        )

        assert res["agent_run"].status == AgentRunStatus.COMPLETED
        assert res["outreach_message"].negotiation_state == "NEGOTIATING_PRICE"
        assert res["outreach_message"].extracted_terms.get("creator_requested_price") == 80000.0
        assert len(res["outreach_message"].conversation_history) >= 2

        # Verify CampaignInfluencer status transitioned to NEGOTIATING
        reloaded_link = (await db_session.execute(
            select(CampaignInfluencer).where(
                CampaignInfluencer.campaign_id == campaign.id,
                CampaignInfluencer.influencer_id == inf.id,
            )
        )).scalar_one()
        assert reloaded_link.status == CampaignInfluencerStatus.NEGOTIATING


@pytest.mark.asyncio
async def test_commercial_term_protection_in_contract_agent(db_session: AsyncSession):
    """Verify that ContractAgent strictly locks user-entered commercial numbers against AI deviation."""
    user_id = uuid.uuid4()
    user = User(id=user_id, email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-ctp-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Tech Brand Launch",
        brand="TechCorp",
        budget=150000.0,
        objective="Drive App Installs",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-ctp-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-ctp-{uuid.uuid4().hex[:6]}",
        name="Tech Reviewer",
        username="tech_reviewer",
        platform="youtube",
        followers=120000,
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
        id=f"outr-ctp-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        channel="EMAIL",
        subject="Collaboration Request",
        body="Initial pitch",
        status="ACCEPTED",
        response_status="ACCEPTED",
        final_amount=75000.0,
        currency="INR",
        deliverables=["2 Instagram Reels + 1 Story"],
        timeline_start="2026-09-01",
        timeline_end="2026-09-15",
        additional_terms="Content approval required before publishing.",
    )
    db_session.add(msg)
    await db_session.commit()

    agent = ContractAgent()
    from app.ai.agents.base import AgentContext
    ctx = AgentContext(db=db_session, campaign=campaign, user=user, extras={"influencer_id": inf.id})
    context_payload = await agent.build_context(ctx)

    # Simulated LLM output that attempts to change the rate from 75,000 to 80,000
    deviant_output = ContractAgentOutput(
        contract_title="Influencer Collaboration Agreement",
        creator_name=inf.name,
        creator_username=inf.username,
        campaign_name=campaign.name,
        agreed_value=80000.0,  # Deviated rate from AI
        currency="USD",  # Deviated currency
        start_date="2026-10-01",
        end_date="2026-10-31",
        payment_due="Net 15",
        risk_level="LOW",
        deliverables=["5 YouTube Videos"],  # Deviated deliverables
        usage_rights="Full rights in perpetuity",
        exclusivity="Category exclusive",
    )

    with patch.object(
        agent,
        "call_llm",
        AsyncMock(
            return_value=AgentResultEnvelope(
                status="COMPLETED",
                summary="AI generated draft",
                confidence=0.95,
                recommendations=[deviant_output.model_dump()],
                data=deviant_output.model_dump(),
                provider="groq",
                model="llama-3.3-70b-versatile",
                provider_latency_ms=100,
                grok_called=True,
            )
        ),
    ):
        result = await agent.execute(ctx)
        # Verify that Commercial Term Protection strictly restored the authoritative user inputs!
        assert result.data["agreed_value"] == 75000.0
        assert result.data["currency"] == "INR"
        assert result.data["deliverables"] == ["2 Instagram Reels + 1 Story"]
        assert result.data["start_date"] == "2026-09-01"
        assert result.data["end_date"] == "2026-09-15"


@pytest.mark.asyncio
async def test_duplicate_contract_prevention(db_session: AsyncSession):
    """Verify that generating a contract twice for the same campaign + creator updates the existing record without creating duplicate entries."""
    user_id = uuid.uuid4()
    user = User(id=user_id, email=f"user_{uuid.uuid4().hex[:6]}@example.com", password_hash="hash", full_name="User")
    db_session.add(user)

    campaign = Campaign(
        id=f"camp-dup-{uuid.uuid4().hex[:6]}",
        owner_id=user.id,
        name="Summer Splash",
        brand="SplashCo",
        budget=100000.0,
        objective="Awareness",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id=f"inf-dup-{uuid.uuid4().hex[:6]}",
        external_id=f"yt-dup-{uuid.uuid4().hex[:6]}",
        name="Sam Creator",
        username="sam_creates",
        platform="youtube",
        followers=70000,
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
        id=f"outr-dup-{uuid.uuid4().hex[:6]}",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        channel="EMAIL",
        subject="Collaboration Request",
        body="Initial pitch",
        status="ACCEPTED",
        response_status="ACCEPTED",
        final_amount=50000.0,
        currency="INR",
        deliverables=["1 Dedicated Video"],
        timeline_start="2026-09-01",
        timeline_end="2026-09-30",
    )
    db_session.add(msg)
    await db_session.commit()

    supervisor = SupervisorAgent(db_session)
    mock_output = ContractAgentOutput(
        contract_title="Influencer Collaboration Agreement",
        creator_name=inf.name,
        creator_username=inf.username,
        campaign_name=campaign.name,
        agreed_value=50000.0,
        currency="INR",
        deliverables=["1 Dedicated Video"],
        start_date="2026-09-01",
        end_date="2026-09-30",
    )

    with patch.object(
        ContractAgent,
        "call_llm",
        AsyncMock(
            return_value=AgentResultEnvelope(
                status="COMPLETED",
                summary="Contract generated",
                confidence=0.95,
                recommendations=[mock_output.model_dump()],
                data=mock_output.model_dump(),
                provider="groq",
                model="llama-3.3-70b-versatile",
                provider_latency_ms=100,
                grok_called=True,
            )
        ),
    ):
        # First execution
        res1 = await supervisor.run_contract(
            campaign=campaign,
            user=user,
            influencer_id=inf.id,
            agreed_terms={"agreed_rate": 50000.0, "deliverables": ["1 Dedicated Video"]},
        )
        assert res1["contract"] is not None
        c1_id = res1["contract"].id

        # Second execution (e.g. user re-runs contract)
        res2 = await supervisor.run_contract(
            campaign=campaign,
            user=user,
            influencer_id=inf.id,
            agreed_terms={"agreed_rate": 55000.0, "deliverables": ["1 Dedicated Video + 1 Story"]},
        )
        assert res2["contract"] is not None
        c2_id = res2["contract"].id

        # Must reuse the same contract record ID
        assert c1_id == c2_id

        # Total contracts in DB for this campaign + influencer must be exactly 1
        all_contracts = (await db_session.execute(
            select(Contract).where(
                (Contract.campaign_id == campaign.id) & (Contract.influencer_id == inf.id)
            )
        )).scalars().all()
        assert len(all_contracts) == 1


@pytest.mark.asyncio
async def test_outreach_acceptance_and_rejection_http_api(client: AsyncClient, db_session: AsyncSession, test_user: User):
    """Verify HTTP POST /acceptance and /rejection endpoints with JSON body."""
    from app.core.security import create_access_token
    token = create_access_token(subject=str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    campaign = Campaign(
        id="camp-http-test",
        owner_id=test_user.id,
        name="Skincare Launch",
        brand="GlowNaturals",
        budget=100000.0,
        objective="Awareness",
        start_date="2026-09-01",
        end_date="2026-09-30",
        workflow_state=WorkflowState.OUTREACH_COMPLETED,
    )
    db_session.add(campaign)

    inf = Influencer(
        id="inf-http-1",
        external_id="yt-http-1",
        name="Makeup Artist",
        username="makeup_artist",
        platform="youtube",
        followers=50000,
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
        id="outr-http-1",
        campaign_id=campaign.id,
        influencer_id=inf.id,
        influencer_name=inf.name,
        influencer_username=inf.username,
        campaign_name=campaign.name,
        channel="EMAIL",
        subject="Collaboration Request",
        body="Initial pitch text",
        status="READY",
    )
    db_session.add(msg)
    await db_session.commit()

    # 1. Test Acceptance endpoint with JSON body
    accept_payload = {
        "response_notes": "Creator agreed via email.",
        "final_amount": 50000.0,
        "currency": "INR",
        "deliverables": ["1 Dedicated Video", "1 Story"],
        "timeline_start": "2026-09-01",
        "timeline_end": "2026-09-15",
        "additional_terms": "3 days review prior to publishing",
    }
    res = await client.post(f"/api/v1/outreach/{msg.id}/acceptance", json=accept_payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ACCEPTED"
    assert (data.get("responseStatus") or data.get("response_status")) == "ACCEPTED"
    assert (data.get("finalAmount") or data.get("final_amount")) == 50000.0
    assert data["deliverables"] == ["1 Dedicated Video", "1 Story"]

    # 2. Test Rejection endpoint with JSON body
    reject_payload = {
        "rejection_reason": "Budget mismatch",
        "rejection_notes": "Creator asked for too much",
    }
    res_rej = await client.post(f"/api/v1/outreach/{msg.id}/rejection", json=reject_payload, headers=headers)
    assert res_rej.status_code == 200
    data_rej = res_rej.json()
    assert data_rej["status"] == "REJECTED"
    assert (data_rej.get("responseStatus") or data_rej.get("response_status")) == "REJECTED"
    assert (data_rej.get("rejectionReason") or data_rej.get("rejection_reason")) == "Budget mismatch"


