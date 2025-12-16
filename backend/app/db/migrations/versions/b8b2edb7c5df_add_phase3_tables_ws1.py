"""Add Phase 3 advisory tables (WS1)

Revision ID: b8b2edb7c5df
Revises: a4f2e8b3c1d5
Create Date: 2025-12-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b8b2edb7c5df'
down_revision = 'a4f2e8b3c1d5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'p3_advisory_signal',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_posting_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('signal_type', sa.Text(), nullable=False),
        sa.Column('signal_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_score', sa.Numeric(5, 4), nullable=False),
        sa.Column('model_version', sa.Text(), nullable=False),
        sa.Column('computed_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('confidence_score BETWEEN 0 AND 1'),
    )

    op.create_table(
        'p3_advisory_budget',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('budget_day', sa.Date(), nullable=False),
        sa.Column('max_advisories', sa.Integer(), nullable=False),
        sa.Column('used_advisories', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('resume_id', 'budget_day'),
    )

    op.create_table(
        'p3_advisory_cache',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('cache_key', sa.Text(), nullable=False),
        sa.Column('signal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('cache_key'),
    )

    op.create_table(
        'p3_feature_state',
        sa.Column('feature_name', sa.Text(), primary_key=True),
        sa.Column('enabled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('rollout_percent', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('rollout_percent BETWEEN 0 AND 100'),
    )

    op.create_index('idx_p3_signal_resume_job', 'p3_advisory_signal', ['resume_id', 'job_posting_id'])
    op.create_index('idx_p3_signal_active', 'p3_advisory_signal', ['is_active'])
    op.create_index('idx_p3_budget_day', 'p3_advisory_budget', ['budget_day'])
    op.create_index('idx_p3_cache_signal', 'p3_advisory_cache', ['signal_id'])

    op.execute(
        """
        INSERT INTO p3_feature_state (feature_name, enabled, rollout_percent)
        VALUES ('p3_advisory', false, 0)
        ON CONFLICT (feature_name) DO NOTHING
        """
    )


def downgrade():
    op.drop_table('p3_advisory_cache')
    op.drop_table('p3_advisory_budget')
    op.drop_table('p3_advisory_signal')
    op.drop_table('p3_feature_state')
