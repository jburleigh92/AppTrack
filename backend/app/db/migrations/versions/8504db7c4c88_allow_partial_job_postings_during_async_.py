"""Allow partial job_postings during async scrape

Revision ID: 8504db7c4c88
Revises: 0001_initial_schema
Create Date: 2025-12-14 12:18:45.030674

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8504db7c4c88'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None

def upgrade():
    op.alter_column("job_postings", "company_name", nullable=True)
    op.alter_column("job_postings", "description", nullable=True)
    op.alter_column("job_postings", "requirements", nullable=True)
    op.alter_column("job_postings", "salary_range", nullable=True)
    op.alter_column("job_postings", "location", nullable=True)
    op.alter_column("job_postings", "employment_type", nullable=True)


def downgrade():
    pass

