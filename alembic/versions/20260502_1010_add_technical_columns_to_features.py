"""add_technical_columns_to_features

Revision ID: 20260502_feat_tech
Revises: 20260501_backtest_wf
Create Date: 2026-05-02 10:10:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '20260502_feat_tech'
down_revision = '20260501_backtest_wf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('features', sa.Column('volatility_10d', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('volatility_20d', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('volatility_ratio_10_20', sa.Numeric(10, 4), nullable=True))

    op.add_column('features', sa.Column('close_vs_sma10_pct', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('close_vs_sma20_pct', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('close_vs_sma50_pct', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('sma10_slope', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('sma20_slope', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('sma50_slope', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('uptrend_alignment', sa.Numeric(10, 4), nullable=True))

    op.add_column('features', sa.Column('volume_zscore_20d', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('volume_ratio_5_20', sa.Numeric(10, 4), nullable=True))

    op.add_column('features', sa.Column('roc_5d', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('roc_10d', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('roc_20d', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('rsi_14', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('stochastic_k_14', sa.Numeric(10, 4), nullable=True))

    op.add_column('features', sa.Column('dist_from_20d_high_pct', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('dist_from_20d_low_pct', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('dist_from_52w_high_pct', sa.Numeric(10, 4), nullable=True))
    op.add_column('features', sa.Column('dist_from_52w_low_pct', sa.Numeric(10, 4), nullable=True))


def downgrade() -> None:
    op.drop_column('features', 'dist_from_52w_low_pct')
    op.drop_column('features', 'dist_from_52w_high_pct')
    op.drop_column('features', 'dist_from_20d_low_pct')
    op.drop_column('features', 'dist_from_20d_high_pct')

    op.drop_column('features', 'stochastic_k_14')
    op.drop_column('features', 'rsi_14')
    op.drop_column('features', 'roc_20d')
    op.drop_column('features', 'roc_10d')
    op.drop_column('features', 'roc_5d')

    op.drop_column('features', 'volume_ratio_5_20')
    op.drop_column('features', 'volume_zscore_20d')

    op.drop_column('features', 'uptrend_alignment')
    op.drop_column('features', 'sma50_slope')
    op.drop_column('features', 'sma20_slope')
    op.drop_column('features', 'sma10_slope')
    op.drop_column('features', 'close_vs_sma50_pct')
    op.drop_column('features', 'close_vs_sma20_pct')
    op.drop_column('features', 'close_vs_sma10_pct')

    op.drop_column('features', 'volatility_ratio_10_20')
    op.drop_column('features', 'volatility_20d')
    op.drop_column('features', 'volatility_10d')
