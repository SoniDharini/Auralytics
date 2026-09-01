"""Database schema auto-migrator.

Inspects SQLite / PostgreSQL tables and adds any missing columns defined in SQLAlchemy models.
"""

import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def auto_migrate_db(engine: AsyncEngine) -> None:
    """Ensure all required columns for all models exist in the database."""
    async with engine.begin() as conn:
        dialect_name = engine.dialect.name

        if dialect_name == "sqlite":
            # 1. Inspect existing columns in contracts table
            res = await conn.execute(text("PRAGMA table_info(contracts);"))
            existing_cols = {row[1] for row in res.fetchall()}

            contract_columns = [
                ("version", "INTEGER DEFAULT 1"),
                ("agent_run_id", "VARCHAR(64)"),
                ("analysis_json", "JSON"),
                ("missing_clauses", "JSON"),
                ("conflicts", "JSON"),
                ("risk_flags", "JSON"),
                ("commercial_terms_match", "JSON"),
                ("overall_status", "VARCHAR(50) DEFAULT 'READY_FOR_REVIEW'"),
                ("approved_by", "VARCHAR(255)"),
                ("approved_at", "DATETIME"),
                ("change_requests", "JSON"),
            ]

            for col_name, col_def in contract_columns:
                if col_name not in existing_cols:
                    logger.info("Auto-migrating SQLite table 'contracts': adding column '%s'", col_name)
                    await conn.execute(text(f"ALTER TABLE contracts ADD COLUMN {col_name} {col_def};"))

            # 2. Inspect outreach_messages
            res_outreach = await conn.execute(text("PRAGMA table_info(outreach_messages);"))
            existing_outreach_cols = {row[1] for row in res_outreach.fetchall()}
            outreach_columns = [
                ("contract_id", "VARCHAR(64)"),
                ("extracted_terms", "JSON"),
                ("conversation_history", "JSON"),
                ("final_amount", "FLOAT"),
                ("currency", "VARCHAR(10) DEFAULT 'INR'"),
                ("deliverables", "JSON"),
                ("timeline_start", "VARCHAR(50)"),
                ("timeline_end", "VARCHAR(50)"),
                ("additional_terms", "VARCHAR(1000)"),
                ("rejection_reason", "VARCHAR(255)"),
                ("rejection_notes", "VARCHAR(2000)"),
            ]
            for col_name, col_def in outreach_columns:
                if col_name not in existing_outreach_cols:
                    logger.info("Auto-migrating SQLite table 'outreach_messages': adding column '%s'", col_name)
                    await conn.execute(text(f"ALTER TABLE outreach_messages ADD COLUMN {col_name} {col_def};"))

        elif dialect_name in ("postgresql", "postgres"):
            # PostgreSQL schema updates using IF NOT EXISTS
            postgres_statements = [
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS agent_run_id VARCHAR(64);",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS analysis_json JSONB;",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS missing_clauses JSONB;",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS conflicts JSONB;",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS risk_flags JSONB;",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS commercial_terms_match JSONB;",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS overall_status VARCHAR(50) DEFAULT 'READY_FOR_REVIEW';",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS approved_by VARCHAR(255);",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP WITH TIME ZONE;",
                "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS change_requests JSONB;",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS contract_id VARCHAR(64);",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS extracted_terms JSONB;",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS conversation_history JSONB;",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS final_amount DOUBLE PRECISION;",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'INR';",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS deliverables JSONB;",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS timeline_start VARCHAR(50);",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS timeline_end VARCHAR(50);",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS additional_terms VARCHAR(1000);",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR(255);",
                "ALTER TABLE outreach_messages ADD COLUMN IF NOT EXISTS rejection_notes VARCHAR(2000);",
            ]
            for stmt in postgres_statements:
                await conn.execute(text(stmt))
