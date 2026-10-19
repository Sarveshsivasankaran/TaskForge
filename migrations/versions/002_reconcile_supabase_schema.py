"""Reconcile Supabase schema with TaskForge ORM models.

Revision ID: 002_reconcile_supabase_schema
Revises: 001_initial_schema
Create Date: 2026-10-19 15:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '002_reconcile_supabase_schema'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # jobs additions
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS attempt_count INTEGER DEFAULT 0;")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS max_attempts INTEGER DEFAULT 5;")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS next_run_at TIMESTAMPTZ;")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_owner VARCHAR(100);")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_token UUID;")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_expires_at TIMESTAMPTZ;")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1;")
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS last_error JSONB;")

    # job_attempts additions
    op.execute("ALTER TABLE job_attempts ADD COLUMN IF NOT EXISTS worker_id VARCHAR(100) DEFAULT 'worker-1';")
    op.execute("ALTER TABLE job_attempts ADD COLUMN IF NOT EXISTS duration_ms BIGINT;")
    op.execute("ALTER TABLE job_attempts ADD COLUMN IF NOT EXISTS error_type VARCHAR(100);")
    op.execute("ALTER TABLE job_attempts ADD COLUMN IF NOT EXISTS result JSONB;")
    op.execute("ALTER TABLE job_attempts ADD COLUMN IF NOT EXISTS lease_token UUID;")

    # job_events additions
    op.execute("ALTER TABLE job_events ADD COLUMN IF NOT EXISTS event_data JSONB;")

    # job_outbox additions
    op.execute("ALTER TABLE job_outbox ADD COLUMN IF NOT EXISTS dispatched BOOLEAN DEFAULT FALSE;")
    op.execute("ALTER TABLE job_outbox ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;")
    op.execute("ALTER TABLE job_outbox ADD COLUMN IF NOT EXISTS dispatched_at TIMESTAMPTZ;")


def downgrade() -> None:
    pass
