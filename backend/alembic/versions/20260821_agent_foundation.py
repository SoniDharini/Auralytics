"""agent runs, campaign strategies, workflow state, approval ownership links

Revision ID: 20260821_agent_foundation
Revises: 20260814_add_camp_infl
Create Date: 2026-08-21 12:00:00.000000

Additive only — preserves users, campaigns, auth, and existing agent/approval UI tables.
Idempotent: safe to re-run if a prior attempt partially applied (e.g. agent_runs already exists).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

import app.db.custom_types

revision: str = "20260821_agent_foundation"
down_revision: Union[str, None] = "20260814_add_camp_infl"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _insp():
    return inspect(op.get_bind())


def _has_table(name: str) -> bool:
    return name in _insp().get_table_names()


def _has_column(table: str, column: str) -> bool:
    if not _has_table(table):
        return False
    return column in {c["name"] for c in _insp().get_columns(table)}


def _has_index(table: str, index_name: str) -> bool:
    if not _has_table(table):
        return False
    return index_name in {idx["name"] for idx in _insp().get_indexes(table)}


def _has_fk(table: str, fk_name: str) -> bool:
    if not _has_table(table):
        return False
    return fk_name in {fk.get("name") for fk in _insp().get_foreign_keys(table)}


def upgrade() -> None:
    if not _has_table("agent_runs"):
        op.create_table(
            "agent_runs",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("user_id", app.db.custom_types.GUID(), nullable=False),
            sa.Column("campaign_id", sa.String(length=64), nullable=False),
            sa.Column("agent_name", sa.String(length=64), nullable=False),
            sa.Column("agent_version", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("trigger", sa.String(length=64), nullable=False),
            sa.Column("input_summary", sa.Text(), nullable=True),
            sa.Column("output_json", app.db.custom_types.JSON_COMPAT(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    for index_name, columns in (
        ("ix_agent_runs_id", ["id"]),
        ("ix_agent_runs_user_id", ["user_id"]),
        ("ix_agent_runs_campaign_id", ["campaign_id"]),
        ("ix_agent_runs_agent_name", ["agent_name"]),
        ("ix_agent_runs_status", ["status"]),
        ("ix_agent_runs_campaign_agent", ["campaign_id", "agent_name"]),
        ("ix_agent_runs_user_status", ["user_id", "status"]),
    ):
        if not _has_index("agent_runs", index_name):
            op.create_index(index_name, "agent_runs", columns)

    if not _has_table("campaign_strategies"):
        op.create_table(
            "campaign_strategies",
            sa.Column("id", sa.String(length=64), nullable=False),
            sa.Column("campaign_id", sa.String(length=64), nullable=False),
            sa.Column("agent_run_id", sa.String(length=64), nullable=True),
            sa.Column("strategy_json", app.db.custom_types.JSON_COMPAT(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("campaign_id", "version", name="uq_campaign_strategy_version"),
        )

    for index_name, columns in (
        ("ix_campaign_strategies_id", ["id"]),
        ("ix_campaign_strategies_campaign_id", ["campaign_id"]),
        ("ix_campaign_strategies_agent_run_id", ["agent_run_id"]),
    ):
        if not _has_index("campaign_strategies", index_name):
            op.create_index(index_name, "campaign_strategies", columns)

    if not _has_column("campaigns", "workflow_state"):
        with op.batch_alter_table("campaigns", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "workflow_state",
                    sa.String(length=64),
                    nullable=False,
                    server_default="CAMPAIGN_CREATED",
                )
            )
    if not _has_index("campaigns", "ix_campaigns_workflow_state"):
        op.create_index("ix_campaigns_workflow_state", "campaigns", ["workflow_state"])

    for col_name, col_def in (
        ("user_id", sa.Column("user_id", app.db.custom_types.GUID(), nullable=True)),
        ("campaign_id", sa.Column("campaign_id", sa.String(length=64), nullable=True)),
        ("agent_run_id", sa.Column("agent_run_id", sa.String(length=64), nullable=True)),
        ("resolved_by", sa.Column("resolved_by", app.db.custom_types.GUID(), nullable=True)),
        ("notes", sa.Column("notes", sa.Text(), nullable=True)),
    ):
        if not _has_column("approvals", col_name):
            with op.batch_alter_table("approvals", schema=None) as batch_op:
                batch_op.add_column(col_def)

    for index_name, columns in (
        ("ix_approvals_user_id", ["user_id"]),
        ("ix_approvals_campaign_id", ["campaign_id"]),
        ("ix_approvals_agent_run_id", ["agent_run_id"]),
    ):
        if not _has_index("approvals", index_name):
            op.create_index(index_name, "approvals", columns)

    if not _has_fk("approvals", "fk_approvals_user_id"):
        with op.batch_alter_table("approvals", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_approvals_user_id", "users", ["user_id"], ["id"], ondelete="CASCADE"
            )
    if not _has_fk("approvals", "fk_approvals_campaign_id"):
        with op.batch_alter_table("approvals", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_approvals_campaign_id", "campaigns", ["campaign_id"], ["id"], ondelete="CASCADE"
            )
    if not _has_fk("approvals", "fk_approvals_agent_run_id"):
        with op.batch_alter_table("approvals", schema=None) as batch_op:
            batch_op.create_foreign_key(
                "fk_approvals_agent_run_id",
                "agent_runs",
                ["agent_run_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    if _has_table("approvals"):
        with op.batch_alter_table("approvals", schema=None) as batch_op:
            if _has_fk("approvals", "fk_approvals_agent_run_id"):
                batch_op.drop_constraint("fk_approvals_agent_run_id", type_="foreignkey")
            if _has_fk("approvals", "fk_approvals_campaign_id"):
                batch_op.drop_constraint("fk_approvals_campaign_id", type_="foreignkey")
            if _has_fk("approvals", "fk_approvals_user_id"):
                batch_op.drop_constraint("fk_approvals_user_id", type_="foreignkey")
            if _has_index("approvals", "ix_approvals_agent_run_id"):
                batch_op.drop_index("ix_approvals_agent_run_id")
            if _has_index("approvals", "ix_approvals_campaign_id"):
                batch_op.drop_index("ix_approvals_campaign_id")
            if _has_index("approvals", "ix_approvals_user_id"):
                batch_op.drop_index("ix_approvals_user_id")
            for col in ("notes", "resolved_by", "agent_run_id", "campaign_id", "user_id"):
                if _has_column("approvals", col):
                    batch_op.drop_column(col)

    if _has_table("campaigns"):
        with op.batch_alter_table("campaigns", schema=None) as batch_op:
            if _has_index("campaigns", "ix_campaigns_workflow_state"):
                batch_op.drop_index("ix_campaigns_workflow_state")
            if _has_column("campaigns", "workflow_state"):
                batch_op.drop_column("workflow_state")

    if _has_table("campaign_strategies"):
        op.drop_table("campaign_strategies")
    if _has_table("agent_runs"):
        op.drop_table("agent_runs")
