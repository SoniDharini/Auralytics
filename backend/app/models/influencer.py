from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.custom_types import JSON_COMPAT


class Influencer(Base):
    __tablename__ = "influencers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    avatar: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    niches: Mapped[List[str]] = mapped_column(JSON_COMPAT(), nullable=False)
    followers: Mapped[int] = mapped_column(Integer, nullable=False)
    engagement_rate: Mapped[float] = mapped_column(Float, nullable=False)
    avg_views: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_likes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_comments: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_match_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    predicted_roas: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    audience_fit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    authenticity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    brand_safety: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    niche_match: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    budget_fit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    audience_gender: Mapped[Dict[str, float]] = mapped_column(JSON_COMPAT(), nullable=False)
    audience_age: Mapped[List[Dict[str, Any]]] = mapped_column(JSON_COMPAT(), nullable=False)
    top_countries: Mapped[List[Dict[str, Any]]] = mapped_column(JSON_COMPAT(), nullable=False)
    top_cities: Mapped[List[str]] = mapped_column(JSON_COMPAT(), nullable=False)
    interests: Mapped[List[str]] = mapped_column(JSON_COMPAT(), nullable=False)
    why_recommended: Mapped[str] = mapped_column(Text, nullable=False)
    shortlisted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="not_contacted", nullable=False)

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
