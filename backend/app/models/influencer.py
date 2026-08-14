from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.custom_types import JSON_COMPAT


class Influencer(Base):
    __tablename__ = "influencers"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_influencer_platform_external_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    profile_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    niches: Mapped[List[str]] = mapped_column(JSON_COMPAT(), default=list, nullable=False)
    followers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    content_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Optional / Unprovided metadata
    business_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    estimated_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ai_match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    predicted_roas: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    audience_fit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    authenticity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    brand_safety: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    niche_match: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    budget_fit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    audience_gender: Mapped[Optional[Dict[str, float]]] = mapped_column(JSON_COMPAT(), nullable=True)
    audience_age: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON_COMPAT(), nullable=True)
    top_countries: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON_COMPAT(), nullable=True)
    top_cities: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    interests: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    why_recommended: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shortlisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="not_contacted", nullable=False)

    data_source: Mapped[str] = mapped_column(String(100), default="youtube", nullable=False)
    source_fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
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

    snapshots: Mapped[List["InfluencerSourceSnapshot"]] = relationship(
        "InfluencerSourceSnapshot",
        back_populates="influencer",
        cascade="all, delete-orphan",
        order_by="InfluencerSourceSnapshot.fetched_at.desc()",
    )


class InfluencerSourceSnapshot(Base):
    __tablename__ = "influencer_source_snapshots"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    influencer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("influencers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON_COMPAT(), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    influencer: Mapped["Influencer"] = relationship("Influencer", back_populates="snapshots")
