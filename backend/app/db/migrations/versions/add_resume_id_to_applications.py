"""add resume_id to applications

Revision ID: add_resume_id_app
Revises: 1b988c67ff99
Create Date: 2025-12-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_resume_id_app'
down_revision = '1b988c67ff99'
branch_labels = None
depends_on = None


def upgrade():
    # Add resume_id column to applications table
    op.add_column('applications',
        sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_applications_resume',
        'applications', 'resumes',
        ['resume_id'], ['id'],
        ondelete='SET NULL'
    )

    # Create index for faster lookups
    op.create_index(
        'idx_applications_resume_id',
        'applications',
        ['resume_id'],
        unique=False
    )


def downgrade():
    # Drop index
    op.drop_index('idx_applications_resume_id', table_name='applications')

    # Drop foreign key constraint
    op.drop_constraint('fk_applications_resume', 'applications', type_='foreignkey')

    # Drop column
    op.drop_column('applications', 'resume_id')
