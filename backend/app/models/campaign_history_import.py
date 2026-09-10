"""Import-specific records. Confirmed campaign data lives on existing Auralytics models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.custom_types import GUID, JSON_COMPAT


class ImportStatus:
    UPLOADED = "UPLOADED"
    PARSED = "PARSED"
    PREVIEW = "PREVIEW"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    ALL = (UPLOADED, PARSED, PREVIEW, CONFIRMED, FAILED, CANCELLED)


class CampaignHistoryImport(Base):
    __tablename__ = "campaign_history_imports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(32), default=ImportStatus.UPLOADED, nullable=False, index=True)
    preview_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON_COMPAT(), nullable=True)
    confirmed_campaign_ids: Mapped[Optional[List[str]]] = mapped_column(JSON_COMPAT(), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    sources: Mapped[List["ImportedSource"]] = relationship(
        "ImportedSource",
        back_populates="import_record",
        cascade="all, delete-orphan",
    )
    provenance: Mapped[List["ImportedFieldProvenance"]] = relationship(
        "ImportedFieldProvenance",
        back_populates="import_record",
        cascade="all, delete-orphan",
    )


class ImportedSource(Base):
    __tablename__ = "imported_sources"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    import_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("campaign_history_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_reference: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_kind: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    import_record: Mapped["CampaignHistoryImport"] = relationship("CampaignHistoryImport", back_populates="sources")


class ImportedFieldProvenance(Base):
    __tablename__ = "imported_field_provenance"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    import_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("campaign_history_imports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    field_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_file_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    import_record: Mapped["CampaignHistoryImport"] = relationship(
        "CampaignHistoryImport", back_populates="provenance"
    )


class AssistantConversation(Base):
    """Persisted assistant transcript. Campaign data is never stored only here."""

    __tablename__ = "assistant_conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    messages: Mapped[List[Dict[str, Any]]] = mapped_column(JSON_COMPAT(), default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
