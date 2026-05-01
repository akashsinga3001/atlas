"""add_ml_pipeline_tables

Revision ID: c2a9d7b1e6f4
Revises: 9f4a1f8c2d7b
Create Date: 2026-05-01 19:15:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c2a9d7b1e6f4'
down_revision = '9f4a1f8c2d7b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ml_training_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('universe', sa.String(length=16), nullable=False),
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('threshold_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('samples_total', sa.Integer(), nullable=False),
        sa.Column('samples_train', sa.Integer(), nullable=False),
        sa.Column('samples_validation', sa.Integer(), nullable=False),
        sa.Column('long_positive_rate_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('short_positive_rate_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('long_metrics', sa.JSON(), nullable=False),
        sa.Column('short_metrics', sa.JSON(), nullable=False),
        sa.Column('feature_columns', sa.JSON(), nullable=False),
        sa.Column('feature_statistics', sa.JSON(), nullable=False),
        sa.Column('long_feature_importance', sa.JSON(), nullable=False),
        sa.Column('short_feature_importance', sa.JSON(), nullable=False),
        sa.Column('long_model_path', sa.String(length=512), nullable=False),
        sa.Column('short_model_path', sa.String(length=512), nullable=False),
        sa.Column('notes', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_date', name='uq_ml_training_runs_run_date'),
    )
    op.create_index('ix_ml_training_runs_status_created_at', 'ml_training_runs', ['status', 'created_at'], unique=False)

    op.create_table(
        'ml_predictions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('training_run_id', sa.Integer(), nullable=False),
        sa.Column('security_id', sa.Integer(), nullable=False),
        sa.Column('prediction_date', sa.Date(), nullable=False),
        sa.Column('ticker', sa.String(length=32), nullable=False),
        sa.Column('direction', sa.String(length=8), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('horizon_days', sa.Integer(), nullable=False),
        sa.Column('threshold_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('top_features', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['training_run_id'], ['ml_training_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['security_id'], ['securities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prediction_date', 'security_id', 'direction', name='uq_ml_predictions_date_security_direction'),
    )
    op.create_index('ix_ml_predictions_training_run_id', 'ml_predictions', ['training_run_id'], unique=False)
    op.create_index('ix_ml_predictions_security_id', 'ml_predictions', ['security_id'], unique=False)
    op.create_index('ix_ml_predictions_date_direction_confidence', 'ml_predictions', ['prediction_date', 'direction', 'confidence'], unique=False)

    op.create_table(
        'ml_reports',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('training_run_id', sa.Integer(), nullable=False),
        sa.Column('report_date', sa.Date(), nullable=False),
        sa.Column('email_to', sa.String(length=255), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=16), nullable=False),
        sa.Column('top_long', sa.JSON(), nullable=False),
        sa.Column('top_short', sa.JSON(), nullable=False),
        sa.Column('html_body', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['training_run_id'], ['ml_training_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_date', name='uq_ml_reports_report_date'),
    )
    op.create_index('ix_ml_reports_status_created_at', 'ml_reports', ['status', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ml_reports_status_created_at', table_name='ml_reports')
    op.drop_table('ml_reports')

    op.drop_index('ix_ml_predictions_date_direction_confidence', table_name='ml_predictions')
    op.drop_index('ix_ml_predictions_security_id', table_name='ml_predictions')
    op.drop_index('ix_ml_predictions_training_run_id', table_name='ml_predictions')
    op.drop_table('ml_predictions')

    op.drop_index('ix_ml_training_runs_status_created_at', table_name='ml_training_runs')
    op.drop_table('ml_training_runs')
