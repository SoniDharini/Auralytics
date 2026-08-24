import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.custom_types import GUID, JSON_COMPAT


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"camp-{uuid.uuid4().hex[:8]}",
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand: Mapped[str] = mapped_column(String(255), default="GlowNaturals", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="planning", nullable=False)
    health: Mapped[str] = mapped_column(String(50), default="healthy", nullable=False)
    budget: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    spend: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    roas: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    influencers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    end_date: Mapped[str] = mapped_column(String(50), nullable=False)
    conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reach: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    objective: Mapped[str] = mapped_column(String(100), default="Product Launch", nullable=False)

    # Detailed setup attributes stored as JSON
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    campaign_types: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    target_locations: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    interests: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    languages: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    platforms: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    creator_tiers: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    budget_allocation: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON_COMPAT(), nullable=True)
    primary_kpi: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    target_roas: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_cpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Creator discovery criteria
    keywords: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    min_followers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_followers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_discovery_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Deterministic Supervisor workflow state (not LLM-inferred).
    workflow_state: Mapped[str] = mapped_column(
        String(64),
        default="CAMPAIGN_CREATED",
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="campaigns")
    activities: Mapped[List["CampaignActivity"]] = relationship(
        "CampaignActivity",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="CampaignActivity.created_at.desc()",
    )
    campaign_influencers: Mapped[List["CampaignInfluencer"]] = relationship(
        "CampaignInfluencer",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    agent_runs: Mapped[List["AgentRun"]] = relationship(
        "AgentRun",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
    strategies: Mapped[List["CampaignStrategy"]] = relationship(
        "CampaignStrategy",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="CampaignStrategy.version.desc()",
    )
