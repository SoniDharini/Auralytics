from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    influencer_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    influencer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    influencer_username: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="EMAIL", nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    short_dm: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    call_to_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personalization_points: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="READY", nullable=False)
    sent_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    negotiation_state: Mapped[Optional[str]] = mapped_column(String(50), default="INITIAL_OUTREACH", nullable=True)
    response_status: Mapped[Optional[str]] = mapped_column(String(50), default="PENDING_RESPONSE", nullable=True)
    response_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    final_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), default="INR", nullable=True)
    deliverables: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    timeline_start: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    timeline_end: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    additional_terms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rejection_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contract_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    extracted_terms: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict, nullable=True)
    conversation_history: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, default=list, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )

