"""Allow completed status in scraper_queue

Revision ID: 1b988c67ff99
Revises: 8504db7c4c88
Create Date: 2025-12-14 12:35:49.912396

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b988c67ff99'
down_revision = '8504db7c4c88'
branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
        ALTER TABLE scraper_queue
        DROP CONSTRAINT chk_scraper_status
    """)
    op.execute("""
        ALTER TABLE scraper_queue
        ADD CONSTRAINT chk_scraper_status
        CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
    """)

def downgrade():
    op.execute("""
        ALTER TABLE scraper_queue
        DROP CONSTRAINT chk_scraper_status
    """)
    op.execute("""
        ALTER TABLE scraper_queue
        ADD CONSTRAINT chk_scraper_status
        CHECK (status IN ('pending', 'processing', 'failed'))
    """)


