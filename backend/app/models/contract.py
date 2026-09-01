import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.db.custom_types import JSON_COMPAT


class ContractStatus:
    NOT_READY = "NOT_READY"
    READY_FOR_CONTRACT = "READY_FOR_CONTRACT"
    DRAFTED = "DRAFTED"
    PENDING_SIGNATURE = "pending_signature"
    ANALYZED = "ANALYZED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    SIGNED = "signed"
    REJECTED = "REJECTED"
    LOCKED = "LOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    campaign_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    influencer_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    outreach_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    agent_run_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    creator: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending_signature", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    end_date: Mapped[str] = mapped_column(String(50), nullable=False)
    payment_due: Mapped[str] = mapped_column(String(50), nullable=False)
    risk: Mapped[str] = mapped_column(String(50), default="low", nullable=False)
    deliverables: Mapped[List[str]] = mapped_column(JSON_COMPAT(), nullable=False)
    usage_rights: Mapped[str] = mapped_column(String(255), nullable=False)
    exclusivity: Mapped[str] = mapped_column(String(255), nullable=False)
    additional_terms: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    contract_body: Mapped[Optional[str]] = mapped_column(String(10000), nullable=True)
    ai_risks: Mapped[List[str]] = mapped_column(JSON_COMPAT(), default=list, nullable=False)

    # Rich analysis & verification metadata
    analysis_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_COMPAT(), default=dict, nullable=True)
    missing_clauses: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), default=list, nullable=True)
    conflicts: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON_COMPAT(), default=list, nullable=True)
    risk_flags: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON_COMPAT(), default=list, nullable=True)
    commercial_terms_match: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_COMPAT(), default=dict, nullable=True)
    overall_status: Mapped[str] = mapped_column(String(50), default="READY_FOR_REVIEW", nullable=False)

    # Human approval & change request tracking
    approved_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    change_requests: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON_COMPAT(), default=list, nullable=True)

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
