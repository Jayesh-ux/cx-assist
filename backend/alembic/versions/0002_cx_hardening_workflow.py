"""Hardening + workflow: agent->brand scoping and stateful-pipeline telemetry.

Adds users.brand_id and the workflow columns on ai_logs. Column types are kept
portable (TEXT for JSON blobs) so the migration also runs on the ephemeral
SQLite deployments that bypass real Postgres/Chroma.

Revision ID: 0002_cx_hardening_workflow
Revises: 0001_initial
Create Date: 2026-09-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_cx_hardening_workflow"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    has_json = bind.dialect.name in ("postgresql",)

    # agents are scoped to a single brand (NULL = no brand assigned yet)
    op.add_column("users", sa.Column("brand_id", sa.String(36), nullable=True))
    try:
        op.create_index("ix_users_brand_id", "users", ["brand_id"])
    except Exception:  # noqa: BLE001 — index may already exist on rerun
        pass

    coltype = sa.JSON() if has_json else sa.Text()
    op.add_column("ai_logs", sa.Column("node_history", coltype, nullable=True))
    op.add_column("ai_logs", sa.Column("grading_results", coltype, nullable=True))
    op.add_column("ai_logs", sa.Column("correction_attempts", sa.Integer(), nullable=True))
    op.add_column("ai_logs", sa.Column("escalation_reason", sa.Text(), nullable=True))
    op.add_column("ai_logs", sa.Column("scraped_content_used", sa.Boolean(), nullable=True))
    op.add_column("ai_logs", sa.Column("validation_status", sa.String(32), nullable=True))
    op.add_column("ai_logs", sa.Column("confidence_score", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("ai_logs", "confidence_score")
    op.drop_column("ai_logs", "validation_status")
    op.drop_column("ai_logs", "scraped_content_used")
    op.drop_column("ai_logs", "escalation_reason")
    op.drop_column("ai_logs", "correction_attempts")
    op.drop_column("ai_logs", "grading_results")
    op.drop_column("ai_logs", "node_history")
    op.drop_index("ix_users_brand_id", table_name="users")
    op.drop_column("users", "brand_id")