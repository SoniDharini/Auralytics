import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.custom_types import JSON_COMPAT


class TrackingStatus:
    NOT_TRACKED = "NOT_TRACKED"
    TRACKING = "TRACKING"
    ACTIVE = "ACTIVE"
    SYNC_FAILED = "SYNC_FAILED"
    COMPLETED = "COMPLETED"

    ALL = (NOT_TRACKED, TRACKING, ACTIVE, SYNC_FAILED, COMPLETED)


class ContentType:
    YOUTUBE_VIDEO = "YOUTUBE_VIDEO"
    YOUTUBE_SHORT = "YOUTUBE_SHORT"

    ALL = (YOUTUBE_VIDEO, YOUTUBE_SHORT)


class PerformanceStatus:
    EARLY_STAGE = "EARLY_STAGE"
    STRONG = "STRONG"
    ON_TRACK = "ON_TRACK"
    AVERAGE = "AVERAGE"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"
    UNDERPERFORMING = "UNDERPERFORMING"

    ALL = (EARLY_STAGE, STRONG, ON_TRACK, AVERAGE, NEEDS_ATTENTION, UNDERPERFORMING)


class ContentStage:
    EARLY_STAGE = "EARLY_STAGE"
    INITIAL_MOMENTUM = "INITIAL_MOMENTUM"
    SHORT_TERM = "SHORT_TERM"
    MATURE = "MATURE"
    LONG_TERM = "LONG_TERM"

    ALL = (EARLY_STAGE, INITIAL_MOMENTUM, SHORT_TERM, MATURE, LONG_TERM)


class ViewMomentum:
    RISING = "RISING"
    STABLE = "STABLE"
    SLOWING = "SLOWING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

    ALL = (RISING, STABLE, SLOWING, INSUFFICIENT_DATA)


class CampaignContent(Base):
    __tablename__ = "campaign_contents"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"ccont-{uuid.uuid4().hex[:12]}",
        index=True,
    )
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

    platform: Mapped[str] = mapped_column(String(50), default="youtube", nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(50), default=ContentType.YOUTUBE_VIDEO, nullable=False)
    external_content_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    content_url: Mapped[str] = mapped_column(String(1000), nullable=False)

    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    channel_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    channel_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    tracking_status: Mapped[str] = mapped_column(
        String(50),
        default=TrackingStatus.TRACKING,
        nullable=False,
        index=True,
    )
    agreed_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Baseline metrics computed against creator's comparable normal uploads
    baseline_median_views: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_avg_views: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_avg_likes: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_avg_comments: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_engagement_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    baseline_sample_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baseline_video_ids: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)

    # Real YouTube metrics from latest capture
    current_views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    current_likes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    current_comments: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Backend-calculated KPIs
    engagement_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    performance_lift_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_per_view: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cost_per_engagement: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    performance_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Deterministic Business Attribution (Supplied by Brand/User — Never Inferred from Views)
    attributed_orders: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_order_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attributed_revenue: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    gross_margin_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attributed_profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    attribution_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    attribution_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def cpm(self) -> Optional[float]:
        """Deterministic Cost Per Mille (CPM / 1,000 views)."""
        if self.agreed_cost is not None and self.current_views and self.current_views > 0:
            return round((self.agreed_cost / self.current_views) * 1000, 2)
        return None

    @property
    def engagement_lift_percent(self) -> Optional[float]:
        """Deterministic engagement lift vs creator upload baseline."""
        if (
            self.engagement_rate is not None
            and self.baseline_engagement_rate is not None
            and self.baseline_engagement_rate > 0
        ):
            return round(
                ((self.engagement_rate - self.baseline_engagement_rate) / self.baseline_engagement_rate) * 100,
                2,
            )
        return None

    @property
    def roas(self) -> Optional[float]:
        """Deterministic ROAS: Attributed Revenue / Campaign Spend."""
        if self.attributed_revenue is not None and self.agreed_cost is not None and self.agreed_cost > 0:
            return round(self.attributed_revenue / self.agreed_cost, 2)
        return None

    @property
    def roi(self) -> Optional[float]:
        """Deterministic ROI: ((Attributed Profit - Campaign Spend) / Campaign Spend) * 100.

        Strictly returns None if profit margin or attributed profit was not supplied.
        Never invents or guesses ROI.
        """
        profit = self.attributed_profit
        if profit is None and self.attributed_revenue is not None and self.gross_margin_percent is not None:
            profit = self.attributed_revenue * (self.gross_margin_percent / 100.0)

        if profit is not None and self.agreed_cost is not None and self.agreed_cost > 0:
            return round(((profit - self.agreed_cost) / self.agreed_cost) * 100.0, 1)
        return None

    @property
    def content_age_hours(self) -> Optional[float]:
        """Content age in hours since published_at."""
        if not self.published_at:
            return None
        now_dt = datetime.now(timezone.utc)
        pub_dt = self.published_at if self.published_at.tzinfo is not None else self.published_at.replace(tzinfo=timezone.utc)
        diff_sec = (now_dt - pub_dt).total_seconds()
        return max(0.0, round(diff_sec / 3600.0, 1))

    @property
    def content_age_days(self) -> Optional[float]:
        """Content age in days since published_at."""
        hours = self.content_age_hours
        if hours is None:
            return None
        return round(hours / 24.0, 1)

    @property
    def content_stage(self) -> str:
        """Performance window stage based on content age."""
        hours = self.content_age_hours
        if hours is None:
            return ContentStage.MATURE
        if hours <= 24.0:
            return ContentStage.EARLY_STAGE
        if hours <= 72.0:
            return ContentStage.INITIAL_MOMENTUM
        if hours <= 168.0:
            return ContentStage.SHORT_TERM
        if hours <= 720.0:
            return ContentStage.MATURE
        return ContentStage.LONG_TERM

    @property
    def momentum(self) -> str:
        """Deterministic momentum classification from snapshot growth history."""
        if not self.snapshots or len(self.snapshots) < 2:
            return ViewMomentum.INSUFFICIENT_DATA

        def _to_utc(dt: Optional[datetime]) -> datetime:
            if dt is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt

        sorted_snaps = sorted(
            self.snapshots,
            key=lambda s: _to_utc(s.captured_at),
        )

        recent = sorted_snaps[-1]
        prev = sorted_snaps[-2]

        r_dt = _to_utc(recent.captured_at)
        p_dt = _to_utc(prev.captured_at)
        dt_sec = max(1.0, (r_dt - p_dt).total_seconds())

        hours = max(1.0, dt_sec / 3600.0)
        views_gained = max(0, recent.views - prev.views)
        velocity = views_gained / hours

        # Compare with earlier velocity if 3+ snapshots exist
        if len(sorted_snaps) >= 3:
            prev2 = sorted_snaps[-3]
            p2_dt = _to_utc(prev2.captured_at)
            dt_sec_prev = max(1.0, (p_dt - p2_dt).total_seconds())
            hours_prev = max(1.0, dt_sec_prev / 3600.0)
            vel_prev = max(0, prev.views - prev2.views) / hours_prev
            if velocity > vel_prev * 1.15:
                return ViewMomentum.RISING
            elif velocity < vel_prev * 0.75:
                return ViewMomentum.SLOWING
            return ViewMomentum.STABLE

        if velocity > 500:
            return ViewMomentum.RISING
        elif velocity > 50:
            return ViewMomentum.STABLE
        return ViewMomentum.SLOWING

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
    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="contents")
    influencer: Mapped["Influencer"] = relationship("Influencer")
    snapshots: Mapped[List["ContentPerformanceSnapshot"]] = relationship(
        "ContentPerformanceSnapshot",
        back_populates="content",
        cascade="all, delete-orphan",
        order_by="ContentPerformanceSnapshot.captured_at.asc()",
        lazy="selectin",
    )



class ContentPerformanceSnapshot(Base):
    __tablename__ = "content_performance_snapshots"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"csnap-{uuid.uuid4().hex[:12]}",
        index=True,
    )
    campaign_content_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("campaign_contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    views: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    likes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    comments: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    # Computed momentum against preceding snapshot
    view_growth_absolute: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    view_growth_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    engagement_growth: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    content: Mapped["CampaignContent"] = relationship("CampaignContent", back_populates="snapshots")
