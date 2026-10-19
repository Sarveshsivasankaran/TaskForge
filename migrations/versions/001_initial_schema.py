"""Initial TaskForge database schema: jobs, job_attempts, job_events, and job_outbox.

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-19 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create 'jobs' table
    op.create_table(
        'jobs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('owner_id', sa.Uuid(), nullable=False),
        sa.Column('job_type', sa.String(length=100), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='queued', nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='5', nullable=False),
        sa.Column('timeout_seconds', sa.Integer(), server_default='300', nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('last_error', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lease_owner', sa.String(length=100), nullable=True),
        sa.Column('lease_token', sa.Uuid(), nullable=True),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_id', 'idempotency_key', name='uq_owner_idempotency_key')
    )
    op.create_index('ix_jobs_owner_id', 'jobs', ['owner_id'])
    op.create_index('ix_jobs_job_type', 'jobs', ['job_type'])
    op.create_index('ix_jobs_status', 'jobs', ['status'])
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'])
    op.create_index('ix_jobs_next_run_at', 'jobs', ['next_run_at'])
    op.create_index('ix_jobs_lease_expires_at', 'jobs', ['lease_expires_at'])
    op.create_index('ix_jobs_idempotency_key', 'jobs', ['idempotency_key'])
    op.create_index('ix_jobs_status_next_run', 'jobs', ['status', 'next_run_at'])
    op.create_index('ix_jobs_lease_recovery', 'jobs', ['status', 'lease_expires_at'])

    # 2. Create 'job_attempts' table
    op.create_table(
        'job_attempts',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('worker_id', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='running', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.BigInteger(), nullable=True),
        sa.Column('error_type', sa.String(length=100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('lease_token', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_job_attempts_job_id', 'job_attempts', ['job_id'])
    op.create_index('ix_job_attempts_job_number', 'job_attempts', ['job_id', 'attempt_number'])

    # 3. Create 'job_events' table
    op.create_table(
        'job_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_job_events_job_id', 'job_events', ['job_id'])
    op.create_index('ix_job_events_event_type', 'job_events', ['event_type'])
    op.create_index('ix_job_events_job_created', 'job_events', ['job_id', 'created_at'])

    # 4. Create 'job_outbox' table
    op.create_table(
        'job_outbox',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('job_id', sa.Uuid(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('dispatched', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_job_outbox_job_id', 'job_outbox', ['job_id'])
    op.create_index('ix_job_outbox_dispatched', 'job_outbox', ['dispatched'])
    op.create_index('ix_job_outbox_pending', 'job_outbox', ['dispatched', 'created_at'])


def downgrade() -> None:
    op.drop_table('job_outbox')
    op.drop_table('job_events')
    op.drop_table('job_attempts')
    op.drop_table('jobs')
