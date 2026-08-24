from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.custom_types import JSON_COMPAT


class CampaignInfluencerStatus:
    """Lifecycle of a creator within one specific campaign."""

    DISCOVERED = "DISCOVERED"
    SHORTLISTED = "SHORTLISTED"
    REJECTED = "REJECTED"
    CONTACTED = "CONTACTED"

    ALL = (DISCOVERED, SHORTLISTED, REJECTED, CONTACTED)


class CampaignInfluencer(Base):
    """Join entity between a campaign and a platform creator.

    The same real creator can be discovered by many campaigns, so campaign specific
    signals (match score, discovery query, shortlist status) live here rather than
    on the globally shared influencer record.
    """

    __tablename__ = "campaign_influencers"
    __table_args__ = (
        UniqueConstraint("campaign_id", "influencer_id", name="uq_campaign_influencer"),
        Index("ix_campaign_influencers_campaign_status", "campaign_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    campaign_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    influencer_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("influencers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Null when the campaign brief did not provide enough real signal to score.
    match_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    match_reasons: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON_COMPAT(), nullable=True)

    discovery_query: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        default=CampaignInfluencerStatus.DISCOVERED,
        nullable=False,
        index=True,
    )

    discovered_at: Mapped[datetime] = mapped_column(
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

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="campaign_influencers")
    influencer: Mapped["Influencer"] = relationship("Influencer", back_populates="campaign_links")
