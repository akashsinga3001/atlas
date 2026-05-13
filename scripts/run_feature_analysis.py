"""Script to run comprehensive feature contribution analysis."""

import argparse
from datetime import date
from pathlib import Path
import sys
from time import perf_counter

import pandas as pd

from config import settings
from services.feature_analysis import FeatureAnalysisService
from utils.logger import logger


def main() -> int:
    """Run feature analysis with configurable parameters."""
    parser = argparse.ArgumentParser(
        description='Analyze feature contribution to stock movement prediction',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze 1DAY timeframe, aggregated across all stocks
  python scripts/run_feature_analysis.py --timeframe 1DAY --output-dir ./artifacts/analysis

  # Analyze all timeframes with stock-level breakdown
  python scripts/run_feature_analysis.py --stock-level --output-dir ./artifacts/analysis

  # Analyze specific date range
  python scripts/run_feature_analysis.py --start-date 2024-01-01 --end-date 2024-12-31
        """,
    )

    parser.add_argument(
        '--timeframe',
        type=str,
        default='1DAY',
        choices=['1DAY', '1WEEK', '1MONTH'],
        help='OHLCV timeframe (default: 1DAY)',
    )
    parser.add_argument(
        '--horizon-days',
        type=int,
        default=20,
        help='Forward-looking window for label computation (default: 20)',
    )
    parser.add_argument(
        '--threshold-pct',
        type=float,
        default=5.0,
        help='Minimum %% move to classify as long/short (default: 5.0)',
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='Optionally filter to start date (YYYY-MM-DD)',
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='Optionally filter to end date (YYYY-MM-DD)',
    )
    parser.add_argument(
        '--stock-level',
        action='store_true',
        default=False,
        help='Include per-stock feature importance breakdown',
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./artifacts/analysis',
        help='Output directory for reports and CSVs (default: ./artifacts/analysis)',
    )
    parser.add_argument(
        '--all-timeframes',
        action='store_true',
        default=False,
        help='Run analysis for all timeframes (1DAY, 1WEEK, 1MONTH)',
    )

    args = parser.parse_args()

    # Parse dates
    train_start_date = None
    train_end_date = None
    if args.start_date:
        try:
            train_start_date = date.fromisoformat(args.start_date)
        except ValueError:
            logger.error('Invalid start-date format. Use YYYY-MM-DD')
            return 1

    if args.end_date:
        try:
            train_end_date = date.fromisoformat(args.end_date)
        except ValueError:
            logger.error('Invalid end-date format. Use YYYY-MM-DD')
            return 1

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info('Output directory: {}', output_dir.resolve())

    # Run analysis
    service = FeatureAnalysisService()
    timeframes = ['1DAY', '1WEEK', '1MONTH'] if args.all_timeframes else [args.timeframe]

    for timeframe in timeframes:
        logger.info('=== Starting analysis for timeframe: {} ===', timeframe)
        started_at = perf_counter()

        try:
            result = service.analyze(
                timeframe=timeframe,
                horizon_days=args.horizon_days,
                threshold_pct=args.threshold_pct,
                train_start_date=train_start_date,
                train_end_date=train_end_date,
                include_stock_level=args.stock_level,
            )

            # Generate HTML report
            html_report = service.generate_html_report(result, timeframe, args.threshold_pct)
            html_path = output_dir / f'feature_analysis_{timeframe}_{date.today().isoformat()}.html'
            html_path.write_text(html_report)
            logger.info('HTML report saved to: {}', html_path)

            # Export feature importance to CSV
            importance_df = pd.DataFrame([
                {
                    'rank': idx + 1,
                    'feature': f.feature_name,
                    'combined_importance': f.combined_importance,
                    'correlation': f.correlation,
                    'mutual_information': f.mutual_information,
                    'spearman_rho': f.spearman_rho,
                    'missing_rate_pct': f.missing_rate_pct,
                    'long_mean': f.long_mean,
                    'neutral_mean': f.neutral_mean,
                    'short_mean': f.short_mean,
                }
                for idx, f in enumerate(result.feature_importance)
            ])
            csv_path = output_dir / f'feature_importance_{timeframe}_{date.today().isoformat()}.csv'
            importance_df.to_csv(csv_path, index=False)
            logger.info('Feature importance CSV saved to: {}', csv_path)

            # Export dataset summary
            summary_data = {
                'Metric': [
                    'Total Records',
                    'Records with Complete Features',
                    'Retention Rate (%)',
                    'Long Moves',
                    'Short Moves',
                    'Neutral',
                    'Timeframe',
                    'Horizon Days',
                    'Threshold (%)',
                ],
                'Value': [
                    result.total_rows,
                    result.rows_retained,
                    round(result.retention_rate_pct, 2),
                    result.long_count,
                    result.short_count,
                    result.neutral_count,
                    timeframe,
                    args.horizon_days,
                    args.threshold_pct,
                ],
            }
            summary_df = pd.DataFrame(summary_data)
            summary_path = output_dir / f'dataset_summary_{timeframe}_{date.today().isoformat()}.csv'
            summary_df.to_csv(summary_path, index=False)
            logger.info('Dataset summary CSV saved to: {}', summary_path)

            # Export missing data analysis
            if result.missing_data:
                missing_df = pd.DataFrame([
                    {'feature': feature, 'missing_rate_pct': rate}
                    for feature, rate in sorted(result.missing_data.items(), key=lambda x: x[1], reverse=True)
                ])
                missing_path = output_dir / f'missing_data_{timeframe}_{date.today().isoformat()}.csv'
                missing_df.to_csv(missing_path, index=False)
                logger.info('Missing data analysis CSV saved to: {}', missing_path)

            # Export per-stock analysis if requested
            if args.stock_level and result.by_stock:
                stock_data = []
                for security_id, analysis in result.by_stock.items():
                    for rank, feature_info in enumerate(analysis.get('top_features', []), 1):
                        stock_data.append({
                            'security_id': security_id,
                            'rank': rank,
                            'feature': feature_info['feature'],
                            'importance': feature_info['importance'],
                            'rows': analysis['rows'],
                        })

                if stock_data:
                    stock_df = pd.DataFrame(stock_data)
                    stock_path = output_dir / f'stock_level_features_{timeframe}_{date.today().isoformat()}.csv'
                    stock_df.to_csv(stock_path, index=False)
                    logger.info('Stock-level analysis CSV saved to: {} ({} stocks)', stock_path, len(result.by_stock))

            elapsed = perf_counter() - started_at
            logger.info(
                'Analysis completed for {} in {:.2f}s | Records: {} | Retained: {:.1f}%',
                timeframe, elapsed, result.total_rows, result.retention_rate_pct
            )

        except Exception as e:
            logger.error('Analysis failed for timeframe={}: {}', timeframe, str(e), exc_info=True)
            return 1

    logger.info('All analyses completed successfully')
    return 0


if __name__ == '__main__':
    sys.exit(main())
