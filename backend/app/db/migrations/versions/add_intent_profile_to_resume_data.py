"""add intent_profile to resume_data

Revision ID: add_intent_profile
Revises: add_resume_id_app
Create Date: 2025-12-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_intent_profile'
down_revision = 'add_resume_id_app'
branch_labels = None
depends_on = None


def upgrade():
    # Add intent_profile column to resume_data table
    op.add_column('resume_data',
        sa.Column('intent_profile', postgresql.JSONB, nullable=True)
    )


def downgrade():
    # Drop column
    op.drop_column('resume_data', 'intent_profile')
