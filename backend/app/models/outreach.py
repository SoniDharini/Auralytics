from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    influencer_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    influencer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    influencer_username: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(50), default="Instagram DM", nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft_ready", nullable=False)
    sent_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
