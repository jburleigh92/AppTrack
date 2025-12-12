"""initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2025-12-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('job_postings',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('job_title', sa.String(length=255), nullable=False),
    sa.Column('company_name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('requirements', sa.Text(), nullable=True),
    sa.Column('salary_range', sa.String(length=100), nullable=True),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('employment_type', sa.String(length=50), nullable=True),
    sa.Column('extraction_complete', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('resumes',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('file_path', sa.Text(), nullable=False),
    sa.Column('file_size_bytes', sa.Integer(), nullable=False),
    sa.Column('mime_type', sa.String(length=100), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('uploaded_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('uploaded', 'processing', 'parsed', 'failed')", name='chk_resume_status'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_resumes_active', 'resumes', ['is_active'], unique=True, postgresql_where=sa.text('is_active = true'))

    op.create_table('settings',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('llm_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('auto_analyze', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('id = 1', name='chk_singleton'),
    sa.PrimaryKeyConstraint('id')
    )

    op.execute("INSERT INTO settings (id, email_config, llm_config, auto_analyze) VALUES (1, '{}', '{}', false)")

    op.create_table('analysis_results',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('job_posting_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('match_score', sa.Integer(), nullable=False),
    sa.Column('qualifications_met', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('qualifications_missing', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('llm_provider', sa.String(length=50), nullable=False),
    sa.Column('llm_model', sa.String(length=100), nullable=False),
    sa.Column('analysis_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('match_score >= 0 AND match_score <= 100', name='chk_match_score'),
    sa.PrimaryKeyConstraint('id')
    )

    op.create_table('applications',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('company_name', sa.String(length=255), nullable=False),
    sa.Column('job_title', sa.String(length=255), nullable=False),
    sa.Column('job_posting_url', sa.Text(), nullable=True),
    sa.Column('application_date', sa.Date(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('source', sa.String(length=50), nullable=False),
    sa.Column('job_board_source', sa.String(length=100), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('needs_review', sa.Boolean(), nullable=False),
    sa.Column('analysis_completed', sa.Boolean(), nullable=False),
    sa.Column('posting_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('analysis_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn')", name='chk_status'),
    sa.CheckConstraint("source IN ('browser', 'email', 'manual')", name='chk_source'),
    sa.CheckConstraint('length(notes) <= 10000', name='chk_notes_length'),
    sa.ForeignKeyConstraint(['analysis_id'], ['analysis_results.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['posting_id'], ['job_postings.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_applications_analysis_id', 'applications', ['analysis_id'], unique=False)
    op.create_index('idx_applications_company_name', 'applications', ['company_name'], unique=False, postgresql_where=sa.text('is_deleted = false'))
    op.create_index('idx_applications_created_at', 'applications', [sa.text('created_at DESC')], unique=False, postgresql_where=sa.text('is_deleted = false'))
    op.create_index('idx_applications_needs_review', 'applications', ['needs_review'], unique=False, postgresql_where=sa.text('needs_review = true AND is_deleted = false'))
    op.create_index('idx_applications_posting_id', 'applications', ['posting_id'], unique=False)
    op.create_index('idx_applications_status', 'applications', ['status'], unique=False, postgresql_where=sa.text('is_deleted = false'))

    op.execute("""
        CREATE INDEX idx_applications_search_gin ON applications 
        USING gin(to_tsvector('english', company_name || ' ' || job_title || ' ' || COALESCE(notes, '')))
    """)

    op.create_table('parser_queue',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('file_path', sa.Text(), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('processing_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('pending', 'processing', 'complete', 'failed')", name='chk_parser_status'),
    sa.CheckConstraint('attempts >= 0', name='chk_parser_attempts'),
    sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_parser_queue_pending', 'parser_queue', ['created_at'], unique=False, postgresql_where=sa.text("status = 'pending'"))
    op.create_index('idx_parser_queue_resume_id', 'parser_queue', ['resume_id'], unique=False)
    op.create_index('idx_parser_queue_stuck', 'parser_queue', ['started_at'], unique=False, postgresql_where=sa.text("status = 'processing'"))

    op.create_table('processed_email_uids',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('email_uid', sa.String(length=255), nullable=False),
    sa.Column('email_account', sa.String(length=255), nullable=False),
    sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email_uid', name='uq_email_uid')
    )
    op.create_index('idx_processed_email_uids_application_id', 'processed_email_uids', ['application_id'], unique=False)
    op.create_index('idx_processed_email_uids_processed_at', 'processed_email_uids', ['processed_at'], unique=False)

    op.create_table('resume_data',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('resume_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=True),
    sa.Column('phone', sa.String(length=50), nullable=True),
    sa.Column('linkedin_url', sa.Text(), nullable=True),
    sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('experience', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('education', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('certifications', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('summary', sa.Text(), nullable=True),
    sa.Column('raw_text_other', sa.Text(), nullable=True),
    sa.Column('extraction_complete', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('resume_id', name='uq_resume_id')
    )
    op.create_index('idx_resume_data_resume_id', 'resume_data', ['resume_id'], unique=False)
    op.create_index('idx_resume_data_skills', 'resume_data', ['skills'], unique=False, postgresql_using='gin')

    op.create_table('scraped_postings',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('html_content', sa.Text(), nullable=False),
    sa.Column('http_status_code', sa.Integer(), nullable=False),
    sa.Column('job_posting_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('scraped_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['job_posting_id'], ['job_postings.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scraped_postings_job_posting_id', 'scraped_postings', ['job_posting_id'], unique=False)

    op.create_table('scraper_queue',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('retry_after', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('processing_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('attempts >= 0', name='chk_scraper_attempts'),
    sa.CheckConstraint("status IN ('pending', 'processing', 'complete', 'failed')", name='chk_scraper_status'),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_scraper_queue_application_id', 'scraper_queue', ['application_id'], unique=False)
    op.create_index('idx_scraper_queue_pending', 'scraper_queue', [sa.text('priority DESC'), 'created_at'], unique=False, postgresql_where=sa.text("status = 'pending'"))
    op.create_index('idx_scraper_queue_stuck', 'scraper_queue', ['started_at'], unique=False, postgresql_where=sa.text("status = 'processing'"))

    op.create_table('timeline_events',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('event_type', sa.String(length=100), nullable=False),
    sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('occurred_at', sa.DateTime(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_timeline_events_application_id', 'timeline_events', ['application_id'], unique=False)
    op.create_index('idx_timeline_events_occurred_at', 'timeline_events', [sa.text('occurred_at DESC')], unique=False)
    op.create_index('idx_timeline_events_type', 'timeline_events', ['event_type'], unique=False)

    op.create_table('analysis_queue',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('application_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('priority', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('attempts', sa.Integer(), nullable=False),
    sa.Column('max_attempts', sa.Integer(), nullable=False),
    sa.Column('retry_after', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('processing_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('attempts >= 0', name='chk_analysis_attempts'),
    sa.CheckConstraint("status IN ('pending', 'processing', 'complete', 'failed')", name='chk_analysis_status'),
    sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_analysis_queue_application_id', 'analysis_queue', ['application_id'], unique=False)
    op.create_index('idx_analysis_queue_pending', 'analysis_queue', [sa.text('priority DESC'), 'created_at'], unique=False, postgresql_where=sa.text("status = 'pending'"))
    op.create_index('idx_analysis_queue_stuck', 'analysis_queue', ['started_at'], unique=False, postgresql_where=sa.text("status = 'processing'"))

    op.execute("""
        ALTER TABLE analysis_results
        ADD CONSTRAINT fk_analysis_application FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE,
        ADD CONSTRAINT fk_analysis_resume FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
        ADD CONSTRAINT fk_analysis_job_posting FOREIGN KEY (job_posting_id) REFERENCES job_postings(id) ON DELETE CASCADE
    """)

    op.create_index('idx_analysis_results_application_id', 'analysis_results', ['application_id'], unique=False)
    op.create_index('idx_analysis_results_job_posting_id', 'analysis_results', ['job_posting_id'], unique=False)
    op.create_index('idx_analysis_results_qualifications', 'analysis_results', ['qualifications_met', 'qualifications_missing'], unique=False, postgresql_using='gin')
    op.create_index('idx_analysis_results_resume_id', 'analysis_results', ['resume_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_analysis_results_resume_id', table_name='analysis_results')
    op.drop_index('idx_analysis_results_qualifications', table_name='analysis_results', postgresql_using='gin')
    op.drop_index('idx_analysis_results_job_posting_id', table_name='analysis_results')
    op.drop_index('idx_analysis_results_application_id', table_name='analysis_results')
    op.drop_index('idx_analysis_queue_stuck', table_name='analysis_queue', postgresql_where=sa.text("status = 'processing'"))
    op.drop_index('idx_analysis_queue_pending', table_name='analysis_queue', postgresql_where=sa.text("status = 'pending'"))
    op.drop_index('idx_analysis_queue_application_id', table_name='analysis_queue')
    op.drop_table('analysis_queue')
    op.drop_index('idx_timeline_events_type', table_name='timeline_events')
    op.drop_index('idx_timeline_events_occurred_at', table_name='timeline_events')
    op.drop_index('idx_timeline_events_application_id', table_name='timeline_events')
    op.drop_table('timeline_events')
    op.drop_index('idx_scraper_queue_stuck', table_name='scraper_queue', postgresql_where=sa.text("status = 'processing'"))
    op.drop_index('idx_scraper_queue_pending', table_name='scraper_queue', postgresql_where=sa.text("status = 'pending'"))
    op.drop_index('idx_scraper_queue_application_id', table_name='scraper_queue')
    op.drop_table('scraper_queue')
    op.drop_index('idx_scraped_postings_job_posting_id', table_name='scraped_postings')
    op.drop_table('scraped_postings')
    op.drop_index('idx_resume_data_skills', table_name='resume_data', postgresql_using='gin')
    op.drop_index('idx_resume_data_resume_id', table_name='resume_data')
    op.drop_table('resume_data')
    op.drop_index('idx_processed_email_uids_processed_at', table_name='processed_email_uids')
    op.drop_index('idx_processed_email_uids_application_id', table_name='processed_email_uids')
    op.drop_table('processed_email_uids')
    op.drop_index('idx_parser_queue_stuck', table_name='parser_queue', postgresql_where=sa.text("status = 'processing'"))
    op.drop_index('idx_parser_queue_resume_id', table_name='parser_queue')
    op.drop_index('idx_parser_queue_pending', table_name='parser_queue', postgresql_where=sa.text("status = 'pending'"))
    op.drop_table('parser_queue')
    op.execute('DROP INDEX idx_applications_search_gin')
    op.drop_index('idx_applications_status', table_name='applications', postgresql_where=sa.text('is_deleted = false'))
    op.drop_index('idx_applications_posting_id', table_name='applications')
    op.drop_index('idx_applications_needs_review', table_name='applications', postgresql_where=sa.text('needs_review = true AND is_deleted = false'))
    op.drop_index('idx_applications_created_at', table_name='applications', postgresql_where=sa.text('is_deleted = false'))
    op.drop_index('idx_applications_company_name', table_name='applications', postgresql_where=sa.text('is_deleted = false'))
    op.drop_index('idx_applications_analysis_id', table_name='applications')
    op.drop_table('applications')
    op.drop_table('analysis_results')
    op.drop_table('settings')
    op.drop_index('idx_resumes_active', table_name='resumes', postgresql_where=sa.text('is_active = true'))
    op.drop_table('resumes')
    op.drop_table('job_postings')
