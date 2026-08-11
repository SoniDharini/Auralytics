from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="idle", nullable=False)
    current_task: Mapped[str] = mapped_column(String(500), nullable=False)
    last_action: Mapped[str] = mapped_column(String(500), nullable=False)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_execution_time: Mapped[str] = mapped_column(String(50), default="2.5s", nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=95.0, nullable=False)
    last_active: Mapped[str] = mapped_column(String(50), default="Just now", nullable=False)
    progress: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    started_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    time: Mapped[str] = mapped_column(String(50), nullable=False)
    agent: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="info", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
