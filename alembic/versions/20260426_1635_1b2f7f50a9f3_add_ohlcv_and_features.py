"""add_ohlcv_and_features

Revision ID: 1b2f7f50a9f3
Revises: f71ffc2dc13e
Create Date: 2026-04-26 16:35:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1b2f7f50a9f3'
down_revision = 'f71ffc2dc13e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ohlcv',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('security_id', sa.Integer(), nullable=False),
        sa.Column('timeframe', sa.String(length=16), nullable=False),
        sa.Column('candle_date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('high', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('low', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('close', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('is_continuous', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['security_id'], ['securities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('security_id', 'timeframe', 'candle_date', name='uq_ohlcv_security_timeframe_candle_date'),
    )
    op.create_index('ix_ohlcv_security_id', 'ohlcv', ['security_id'], unique=False)
    op.create_index('ix_ohlcv_timeframe_candle_date', 'ohlcv', ['timeframe', 'candle_date'], unique=False)
    op.create_index('ix_ohlcv_security_timeframe', 'ohlcv', ['security_id', 'timeframe'], unique=False)

    op.create_table(
        'features',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ohlcv_id', sa.Integer(), nullable=False),
        sa.Column('body_size_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('upper_wick_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('lower_wick_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('range_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('close_position_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('bias', sa.String(length=16), nullable=False),
        sa.Column('candle_type', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ohlcv_id'], ['ohlcv.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ohlcv_id', name='uq_features_ohlcv_id'),
    )
    op.create_index('ix_features_ohlcv_id', 'features', ['ohlcv_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_features_ohlcv_id', table_name='features')
    op.drop_table('features')

    op.drop_index('ix_ohlcv_security_timeframe', table_name='ohlcv')
    op.drop_index('ix_ohlcv_timeframe_candle_date', table_name='ohlcv')
    op.drop_index('ix_ohlcv_security_id', table_name='ohlcv')
    op.drop_table('ohlcv')
