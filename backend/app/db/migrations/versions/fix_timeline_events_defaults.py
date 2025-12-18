"""fix timeline_events timestamp defaults

Revision ID: fix_timeline_defaults
Revises: add_resume_id_app
Create Date: 2025-12-18

Description:
Adds database-level DEFAULT now() to timeline_events.occurred_at and created_at.

Root cause: The initial migration created these columns as NOT NULL without defaults,
while the ORM model assumes server_default=func.now(). This caused NOT NULL violations
when SQLAlchemy omitted these columns from INSERT statements.

This migration aligns the database schema with ORM expectations.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_timeline_defaults'
down_revision = 'add_resume_id_app'
branch_labels = None
depends_on = None


def upgrade():
    # Add DEFAULT now() to occurred_at
    op.execute("""
        ALTER TABLE timeline_events
        ALTER COLUMN occurred_at SET DEFAULT now()
    """)

    # Add DEFAULT now() to created_at
    op.execute("""
        ALTER TABLE timeline_events
        ALTER COLUMN created_at SET DEFAULT now()
    """)


def downgrade():
    # Remove default from occurred_at
    op.execute("""
        ALTER TABLE timeline_events
        ALTER COLUMN occurred_at DROP DEFAULT
    """)

    # Remove default from created_at
    op.execute("""
        ALTER TABLE timeline_events
        ALTER COLUMN created_at DROP DEFAULT
    """)
