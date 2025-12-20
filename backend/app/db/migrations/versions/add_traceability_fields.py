"""add traceability fields to job_postings

Revision ID: add_traceability_fields
Revises: add_job_indexing
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_traceability_fields'
down_revision = 'add_job_indexing'
branch_labels = None
depends_on = None


def upgrade():
    # Add required traceability fields for production ingestion
    op.add_column('job_postings',
        sa.Column('source_query', sa.String(length=200), nullable=True)
    )
    op.add_column('job_postings',
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('job_postings',
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column('job_postings',
        sa.Column('industry', sa.String(length=100), nullable=True)
    )

    # Add indexes for traceability queries
    op.create_index('idx_job_postings_source_query', 'job_postings', ['source_query'])
    op.create_index('idx_job_postings_posted_at', 'job_postings', ['posted_at'])
    op.create_index('idx_job_postings_industry', 'job_postings', ['industry'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_job_postings_industry', 'job_postings')
    op.drop_index('idx_job_postings_posted_at', 'job_postings')
    op.drop_index('idx_job_postings_source_query', 'job_postings')

    # Drop columns
    op.drop_column('job_postings', 'industry')
    op.drop_column('job_postings', 'posted_at')
    op.drop_column('job_postings', 'source_timestamp')
    op.drop_column('job_postings', 'source_query')
