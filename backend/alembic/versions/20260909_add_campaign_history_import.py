"""Add campaign history import, provenance, and assistant conversation tables

Revision ID: 20260909_add_hist_import
Revises: 20260905_add_camp_content
Create Date: 2026-09-09 22:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from app.db.custom_types import GUID, JSON_COMPAT

revision = "20260909_add_hist_import"
down_revision = "20260905_add_camp_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "campaign_history_imports",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("preview_json", JSON_COMPAT(), nullable=True),
        sa.Column("confirmed_campaign_ids", JSON_COMPAT(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_campaign_history_imports_user_id", "campaign_history_imports", ["user_id"])
    op.create_index("ix_campaign_history_imports_status", "campaign_history_imports", ["status"])

    op.create_table(
        "imported_sources",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "import_id",
            sa.String(length=64),
            sa.ForeignKey("campaign_history_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("storage_reference", sa.String(length=1000), nullable=False),
        sa.Column("source_kind", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_imported_sources_import_id", "imported_sources", ["import_id"])

    op.create_table(
        "imported_field_provenance",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column(
            "import_id",
            sa.String(length=64),
            sa.ForeignKey("campaign_history_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("field_value", sa.Text(), nullable=True),
        sa.Column("source_file_id", sa.String(length=64), nullable=True),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_imported_field_provenance_import_id", "imported_field_provenance", ["import_id"])

    op.create_table(
        "assistant_conversations",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", GUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("messages", JSON_COMPAT(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assistant_conversations_user_id", "assistant_conversations", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_table("assistant_conversations")
    op.drop_table("imported_field_provenance")
    op.drop_table("imported_sources")
    op.drop_table("campaign_history_imports")
