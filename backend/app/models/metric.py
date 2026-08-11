from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.custom_types import JSON_COMPAT


class MetricCard(Base):
    __tablename__ = "metric_cards"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    context: Mapped[str] = mapped_column(String(255), nullable=False)
    trend_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    trend_positive: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    sparkline: Mapped[Optional[List[float]]] = mapped_column(JSON_COMPAT(), nullable=True)


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="opportunity", nullable=False)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(String(50), nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    action_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)


class OptimizationRec(Base):
    __tablename__ = "optimization_recs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    current_data: Mapped[Dict[str, Any]] = mapped_column(JSON_COMPAT(), nullable=False)
    moves: Mapped[List[Dict[str, Any]]] = mapped_column(JSON_COMPAT(), nullable=False)
    expected_revenue: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
