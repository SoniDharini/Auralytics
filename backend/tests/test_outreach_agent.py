import pytest
import uuid
import json
from datetime import datetime, timezone
from unittest.mock import patch
from httpx import AsyncClient
from app.ai.agents.base import AgentContext
from app.ai.agents.outreach import OutreachAgent, OutreachAgentOutput
from app.ai.agents.supervisor import SupervisorAgent
from app.ai.workflow_states import WorkflowState
from app.core.exceptions import AIProviderException
from app.models.campaign import Campaign
from app.models.campaign_influencer import CampaignInfluencer, CampaignInfluencerStatus
from app.models.influencer import Influencer
from app.models.outreach import OutreachMessage


@pytest.mark.asyncio
async def test_outreach_agent_output_schema_validation():
    output = OutreachAgentOutput(
        influencer_id="inf-test-1",
        channel="EMAIL",
        subject="Collaboration Opportunity with GlowNaturals",
        message="Hi Beauty Creator, we love your skincare videos!",
        short_dm="Hi! We love your content and would love to collaborate.",
        call_to_action="Would you be open to discussing this collaboration?",
        personalization_points=["High skincare audience fit", "Matches campaign objective"],
        confidence=0.94,
    )
    assert output.influencer_id == "inf-test-1"
    assert output.channel == "EMAIL"
    assert output.confidence == 0.94
    assert len(output.personalization_points) == 2


@pytest.mark.asyncio
async def test_supervisor_run_outreach_flow(db_session, test_user):
    now = datetime.now(timezone.utc)
    # 1. Create a test campaign
    camp = Campaign(
        id=f"camp-outr-{uuid.uuid4().hex[:6]}",
        owner_id=test_user.id,
        name="Outreach Test Campaign",
        brand="Test Brand",
        status="active",
        health="healthy",
        budget=100000.0,
        objective="Brand Awareness",
        workflow_state=WorkflowState.SHORTLIST_APPROVED,
        start_date=now,
        end_date=now,
    )
    db_session.add(camp)

    # 2. Create test influencer
    inf = Influencer(
        id=f"inf-outr-{uuid.uuid4().hex[:6]}",
        platform="youtube",
        external_id="yt-channel-123",
        username="glowbeauty",
        name="Glow Beauty",
        profile_url="https://youtube.com/@glowbeauty",
        followers=150000,
        engagement_rate=4.5,
        niches=["Skincare", "Beauty"],
        business_email="glow@business.com",
    )
    db_session.add(inf)
    await db_session.flush()

    link = CampaignInfluencer(
        id=f"link-{uuid.uuid4().hex[:6]}",
        campaign_id=camp.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.SHORTLISTED,
        match_reasons=[
            {
                "source": "discovery_agent_grok",
                "key": "ai_discovery",
                "rank": 1,
                "ai_fit_score": 92.0,
                "campaign_fit": "EXCELLENT",
                "recommendation_reason": "Top skincare channel with high engagement",
                "strengths": ["High retention"],
                "risks": [],
            }
        ],
    )
    db_session.add(link)
    await db_session.commit()

    # 3. Run Supervisor Outreach Agent
    supervisor = SupervisorAgent(db_session)
    result = await supervisor.run_outreach(campaign=camp, user=test_user, influencer_id=inf.id)

    assert result["campaign_id"] == camp.id
    assert result["outreach_message"] is not None
    msg = result["outreach_message"]
    assert msg.influencer_id == inf.id
    assert msg.influencer_name == "Glow Beauty"
    assert msg.subject is not None
    assert "Hi" in msg.body or "Hello" in msg.body or "Glow" in msg.body
    assert msg.status == "READY"


@pytest.mark.asyncio
async def test_contact_info_rule_no_fake_emails(db_session, test_user):
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id=f"camp-noemail-{uuid.uuid4().hex[:6]}",
        owner_id=test_user.id,
        name="No Email Campaign",
        brand="Brand X",
        status="active",
        health="healthy",
        budget=50000.0,
        objective="Test",
        workflow_state=WorkflowState.SHORTLIST_APPROVED,
        start_date=now,
        end_date=now,
    )
    db_session.add(camp)

    # Influencer without email
    inf = Influencer(
        id=f"inf-noemail-{uuid.uuid4().hex[:6]}",
        platform="instagram",
        external_id="ig-noemail-1",
        username="noemailcreator",
        name="No Email Creator",
        followers=50000,
        business_email=None,
    )
    db_session.add(inf)
    await db_session.flush()

    link = CampaignInfluencer(
        id=f"link-noemail-{uuid.uuid4().hex[:6]}",
        campaign_id=camp.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.SHORTLISTED,
    )
    db_session.add(link)
    await db_session.commit()

    agent = OutreachAgent()
    ctx = AgentContext(user=test_user, campaign=camp, db=db_session, extras={"influencer_id": inf.id})
    payload = await agent.build_context(ctx)

    contact_info = payload["influencer"]["contact_info"]
    assert contact_info["email"] == "Not publicly available"
    assert contact_info["instagram"] == "@noemailcreator"
    assert payload["influencer"]["contact_status"] == "CONTACT_REQUIRED"


@pytest.mark.asyncio
async def test_multiple_shortlisted_creators_get_separate_drafts(db_session, test_user):
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id=f"camp-multi-{uuid.uuid4().hex[:6]}",
        owner_id=test_user.id,
        name="Multi Creator Campaign",
        brand="Brand Multi",
        status="active",
        health="healthy",
        budget=80000.0,
        objective="Awareness",
        workflow_state=WorkflowState.SHORTLIST_APPROVED,
        start_date=now,
        end_date=now,
    )
    db_session.add(camp)

    inf_a = Influencer(
        id=f"inf-a-{uuid.uuid4().hex[:6]}",
        platform="youtube",
        external_id="yt-a-1",
        username="creatorA",
        name="Creator A",
        business_email="a@creator.com",
    )
    inf_b = Influencer(
        id=f"inf-b-{uuid.uuid4().hex[:6]}",
        platform="instagram",
        external_id="ig-b-1",
        username="creatorB",
        name="Creator B",
        business_email="b@creator.com",
    )
    db_session.add_all([inf_a, inf_b])
    await db_session.flush()

    link_a = CampaignInfluencer(
        id=f"link-a-{uuid.uuid4().hex[:6]}",
        campaign_id=camp.id,
        influencer_id=inf_a.id,
        status=CampaignInfluencerStatus.SHORTLISTED,
    )
    link_b = CampaignInfluencer(
        id=f"link-b-{uuid.uuid4().hex[:6]}",
        campaign_id=camp.id,
        influencer_id=inf_b.id,
        status=CampaignInfluencerStatus.SHORTLISTED,
    )
    db_session.add_all([link_a, link_b])
    await db_session.commit()

    from app.ai.schemas import LLMRawResponse, LLMUsage

    async def _fake_generate(*, system_prompt, user_prompt, temperature=0.2, max_tokens=4096, response_model=None):
        inf_id = inf_a.id if inf_a.id in user_prompt else inf_b.id
        name = "Creator A" if inf_id == inf_a.id else "Creator B"
        payload = {
            "influencer_id": inf_id,
            "channel": "EMAIL",
            "subject": f"Collab with {name}",
            "message": f"Hi {name}, we'd love to collaborate.",
            "short_dm": f"Hi {name}! Open to a collab?",
            "call_to_action": "Would you be open to discussing this collaboration?",
            "personalization_points": ["Niche fit"],
            "confidence": 0.9,
        }
        return LLMRawResponse(
            content=json.dumps(payload),
            model="test-mock",
            provider="mock",
            latency_ms=1.0,
            usage=LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )

    supervisor = SupervisorAgent(db_session)
    with patch("app.ai.providers.grok.GrokProvider.generate", side_effect=_fake_generate):
        res_a = await supervisor.run_outreach(campaign=camp, user=test_user, influencer_id=inf_a.id)
        camp = await db_session.get(Campaign, camp.id)
        res_b = await supervisor.run_outreach(campaign=camp, user=test_user, influencer_id=inf_b.id)

    msg_a = res_a["outreach_message"]
    msg_b = res_b["outreach_message"]

    assert msg_a is not None and msg_b is not None
    assert msg_a.id != msg_b.id
    assert msg_a.influencer_id == inf_a.id
    assert msg_b.influencer_id == inf_b.id
    assert msg_a.influencer_name == "Creator A"
    assert msg_b.influencer_name == "Creator B"


@pytest.mark.asyncio
async def test_grok_failure_marks_agent_run_failed(db_session, test_user):
    now = datetime.now(timezone.utc)
    camp = Campaign(
        id=f"camp-fail-{uuid.uuid4().hex[:6]}",
        owner_id=test_user.id,
        name="Fail Campaign",
        brand="Brand Fail",
        status="active",
        health="healthy",
        budget=20000.0,
        objective="Test Fail",
        workflow_state=WorkflowState.SHORTLIST_APPROVED,
        start_date=now,
        end_date=now,
    )
    db_session.add(camp)

    inf = Influencer(
        id=f"inf-fail-{uuid.uuid4().hex[:6]}",
        platform="youtube",
        external_id="yt-fail-1",
        username="failcreator",
        name="Fail Creator",
    )
    db_session.add(inf)
    await db_session.flush()

    link = CampaignInfluencer(
        id=f"link-fail-{uuid.uuid4().hex[:6]}",
        campaign_id=camp.id,
        influencer_id=inf.id,
        status=CampaignInfluencerStatus.SHORTLISTED,
    )
    db_session.add(link)
    await db_session.commit()

    supervisor = SupervisorAgent(db_session)

    with patch("app.ai.providers.grok.GrokProvider.generate", side_effect=AIProviderException(detail="Groq authentication failed (check GROQ_API_KEY)")):
        res = await supervisor.run_outreach(campaign=camp, user=test_user, influencer_id=inf.id)
        agent_run = res.get("agent_run")
        assert agent_run is not None
        assert agent_run.status == "FAILED"
        assert "Groq authentication failed" in agent_run.error_message
