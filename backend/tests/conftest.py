import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Set test environment
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "development"

from app.core.config import settings
from app.models import (
    Base,
    User,
    Campaign,
    CampaignActivity,
    CampaignInfluencer,
    CampaignStrategy,
    Influencer,
    OutreachMessage,
    Agent,
    AgentRun,
    Approval,
)
from app.db.session import get_db
from app.main import app

from sqlalchemy.pool import StaticPool

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
test_session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


import uuid
from datetime import datetime, timezone
from app.core.security import get_password_hash
from app.models.user import User
from app.db.seed import ensure_default_agents

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_session_factory() as session:
        await ensure_default_agents(session)
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
        session.add(demo_user)
        await session.commit()

    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)



@pytest_asyncio.fixture
async def db_session(setup_test_db):
    async with test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_user(db_session):
    result = await db_session.execute(select(User).limit(1))
    return result.scalar_one()


async def override_get_db():
    async with test_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
