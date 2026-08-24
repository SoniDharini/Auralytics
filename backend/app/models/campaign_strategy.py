"""Persisted Strategy Agent output — PostgreSQL is the source of truth."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.custom_types import JSON_COMPAT


class CampaignStrategy(Base):
    __tablename__ = "campaign_strategies"
    __table_args__ = (
        UniqueConstraint("campaign_id", "version", name="uq_campaign_strategy_version"),
    )

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: f"strat-{uuid.uuid4().hex[:12]}",
        index=True,
    )
    campaign_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    agent_run_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("agent_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    strategy_json: Mapped[Dict[str, Any]] = mapped_column(JSON_COMPAT(), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
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

    campaign: Mapped["Campaign"] = relationship("Campaign", back_populates="strategies")
