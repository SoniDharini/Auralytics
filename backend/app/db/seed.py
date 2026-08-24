import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import async_session_factory
from app.models.agent_run import Agent
from app.models.campaign import Campaign
from app.models.campaign_activity import CampaignActivity
from app.models.user import User

DEFAULT_AGENTS = [
    {
        "id": "agent-supervisor",
        "name": "Supervisor Agent",
        "role": "Campaign Orchestrator & Coordinator",
        "current_task": "Awaiting campaign workflow",
        "last_action": "Standing by to coordinate agents",
    },
    {
        "id": "agent-strategy",
        "name": "Strategy Agent",
        "role": "Budget Allocation & Creator Mix Strategy",
        "current_task": "Awaiting campaign brief",
        "last_action": "Standing by for audience analysis",
    },
    {
        "id": "agent-discovery",
        "name": "Discovery Agent",
        "role": "Influencer Search & Audience Fit Scoring",
        "current_task": "Awaiting creator discovery trigger",
        "last_action": "Standing by to acquire real creator data",
    },
    {
        "id": "agent-outreach",
        "name": "Outreach Agent",
        "role": "Personalized DM & Email Communication",
        "current_task": "Awaiting shortlisted creators",
        "last_action": "Standing by for pitch preparation",
    },
    {
        "id": "agent-contract",
        "name": "Contract Agent",
        "role": "Contract Generation & AI Risk Review",
        "current_task": "Awaiting agreement terms",
        "last_action": "Standing by for clause verification",
    },
    {
        "id": "agent-performance",
        "name": "Performance Agent",
        "role": "Real-time Tracking & ROI Optimization",
        "current_task": "Awaiting live campaign metrics",
        "last_action": "Standing by for ROAS tracking",
    },
    {
        "id": "agent-optimization",
        "name": "Optimization Agent",
        "role": "Budget & ROI Optimization Proposals",
        "current_task": "Awaiting performance insights",
        "last_action": "Standing by for optimization proposals",
    },
]


async def ensure_default_agents(db) -> None:
    """Idempotent: insert missing agent catalog cards without resetting live status."""
    for spec in DEFAULT_AGENTS:
        existing = await db.execute(select(Agent).where(Agent.id == spec["id"]))
        if existing.scalar_one_or_none() is not None:
            continue
        db.add(
            Agent(
                id=spec["id"],
                name=spec["name"],
                role=spec["role"],
                status="idle",
                current_task=spec["current_task"],
                last_action=spec["last_action"],
                tasks_completed=0,
                avg_execution_time="0.0s",
                success_rate=100.0,
                last_active="Idle",
                progress=0,
                started_at="Idle",
            )
        )


async def seed_database():
    """Seed initial demo user and default agents if database is empty."""
    async with async_session_factory() as db:
        # Always ensure agent catalog cards exist (safe for existing DBs).
        await ensure_default_agents(db)
        await db.commit()

        res = await db.execute(select(User).limit(1))
        if res.scalar_one_or_none() is not None:
            return

        print("Seeding initial database data...")

        demo_user = User(
            id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            full_name="Aaditya Sharma",
            email="aaditya@glownaturals.com",
            password_hash=get_password_hash("password123"),
            company_name="GlowNaturals",
            role="marketing_manager",
            is_active=True,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(demo_user)
        await db.flush()

        campaign = Campaign(
            id="camp-1",
            owner_id=demo_user.id,
            name="GlowNaturals Summer Launch",
            brand="GlowNaturals",
            status="active",
            health="healthy",
            budget=200000,
            spend=0,
            revenue=0,
            roas=0.0,
            influencers=0,
            progress=20,
            start_date="2026-08-20",
            end_date="2026-09-20",
            conversions=0,
            reach=0,
            objective="Product Launch",
            description="Summer skincare and hydration launch across micro and mid-tier creators.",
            target_locations="India",
            interests=["Skincare", "Clean Beauty", "Dermatology"],
            platforms=["youtube", "instagram"],
            workflow_state="CAMPAIGN_CREATED",
        )
        db.add(campaign)
        await db.flush()

        activity = CampaignActivity(
            id="act-seed-1",
            user_id=demo_user.id,
            campaign_id=campaign.id,
            activity_type="CAMPAIGN_CREATED",
            title="Campaign created",
            description="GlowNaturals Summer Launch campaign initialized.",
        )
        db.add(activity)

        await db.commit()
        print("Database seeding completed without fake influencers.")
