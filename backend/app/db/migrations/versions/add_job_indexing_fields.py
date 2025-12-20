"""add job indexing fields for ingestion

Revision ID: add_job_indexing
Revises: add_intent_profile
Create Date: 2025-12-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_job_indexing'
down_revision = 'add_intent_profile'
branch_labels = None
depends_on = None


def upgrade():
    # Add ingestion metadata fields to job_postings table
    op.add_column('job_postings',
        sa.Column('source', sa.String(length=50), nullable=True)
    )
    op.add_column('job_postings',
        sa.Column('external_url', sa.Text(), nullable=True)
    )
    op.add_column('job_postings',
        sa.Column('external_id', sa.String(length=200), nullable=True)
    )

    # Add indexes for search performance
    op.create_index('idx_job_postings_source', 'job_postings', ['source'])
    op.create_index('idx_job_postings_external_id', 'job_postings', ['external_id'])
    op.create_index('idx_job_postings_job_title', 'job_postings', ['job_title'])
    op.create_index('idx_job_postings_company_name', 'job_postings', ['company_name'])
    op.create_index('idx_job_postings_location', 'job_postings', ['location'])
    op.create_index('idx_job_postings_created_at', 'job_postings', ['created_at'])

    # Add composite index for title + company search
    op.create_index('idx_job_postings_title_company', 'job_postings', ['job_title', 'company_name'])

    # Add unique index for deduplication (source + external_id must be unique together)
    op.create_index('idx_job_postings_source_external_id', 'job_postings', ['source', 'external_id'], unique=True)


def downgrade():
    # Drop indexes
    op.drop_index('idx_job_postings_source_external_id', 'job_postings')
    op.drop_index('idx_job_postings_title_company', 'job_postings')
    op.drop_index('idx_job_postings_created_at', 'job_postings')
    op.drop_index('idx_job_postings_location', 'job_postings')
    op.drop_index('idx_job_postings_company_name', 'job_postings')
    op.drop_index('idx_job_postings_job_title', 'job_postings')
    op.drop_index('idx_job_postings_external_id', 'job_postings')
    op.drop_index('idx_job_postings_source', 'job_postings')

    # Drop columns
    op.drop_column('job_postings', 'external_id')
    op.drop_column('job_postings', 'external_url')
    op.drop_column('job_postings', 'source')
