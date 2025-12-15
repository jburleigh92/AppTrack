"""Make scraper_queue.application_id nullable

Revision ID: a4f2e8b3c1d5
Revises: 1b988c67ff99
Create Date: 2025-12-15 02:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a4f2e8b3c1d5'
down_revision = '1b988c67ff99'
branch_labels = None
depends_on = None

def upgrade():
    # Make application_id nullable
    op.alter_column('scraper_queue', 'application_id',
               existing_type=postgresql.UUID(),
               nullable=True)

def downgrade():
    # Make application_id NOT nullable again
    op.alter_column('scraper_queue', 'application_id',
               existing_type=postgresql.UUID(),
               nullable=False)
