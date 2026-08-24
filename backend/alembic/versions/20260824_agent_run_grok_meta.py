"""Add Grok provider metadata columns to agent_runs.

Revision ID: 20260824_agent_run_grok_meta
Revises: 20260821_agent_foundation
Create Date: 2026-08-24 12:00:00.000000

Idempotent — safe if columns already exist.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "20260824_agent_run_grok_meta"
down_revision: Union[str, None] = "20260821_agent_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _insp():
    return inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    if table not in _insp().get_table_names():
        return False
    return column in {c["name"] for c in _insp().get_columns(table)}


def upgrade() -> None:
    if not _has_column("agent_runs", "provider"):
        with op.batch_alter_table("agent_runs", schema=None) as batch_op:
            batch_op.add_column(sa.Column("provider", sa.String(length=32), nullable=True))
    if not _has_column("agent_runs", "model"):
        with op.batch_alter_table("agent_runs", schema=None) as batch_op:
            batch_op.add_column(sa.Column("model", sa.String(length=128), nullable=True))
    if not _has_column("agent_runs", "provider_latency_ms"):
        with op.batch_alter_table("agent_runs", schema=None) as batch_op:
            batch_op.add_column(sa.Column("provider_latency_ms", sa.Float(), nullable=True))


def downgrade() -> None:
    if _has_column("agent_runs", "provider_latency_ms"):
        with op.batch_alter_table("agent_runs", schema=None) as batch_op:
            batch_op.drop_column("provider_latency_ms")
    if _has_column("agent_runs", "model"):
        with op.batch_alter_table("agent_runs", schema=None) as batch_op:
            batch_op.drop_column("model")
    if _has_column("agent_runs", "provider"):
        with op.batch_alter_table("agent_runs", schema=None) as batch_op:
            batch_op.drop_column("provider")
