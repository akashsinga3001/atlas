"""Run end-to-end quantitative feature engineering and research pipeline.

Example:
    py scripts/run_quant_feature_research.py --config backtesting/configs/quant_feature_research.yaml
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path
import json

from backtesting.config import load_research_config
from backtesting.feature_engineering.pipeline import FeatureDatasetPipeline
from backtesting.research.analysis import FeatureResearchAnalyzer
from backtesting.research.regime import RegimeAnalyzer
from backtesting.research.visualization import ResearchVisualizer
from backtesting.training.pipeline import BaselineModelTrainingPipeline
from utils.logger import logger


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for quant research execution."""
    parser = argparse.ArgumentParser(description='Run quantitative feature research pipeline')
    parser.add_argument(
        '--config',
        type=str,
        default='backtesting/configs/quant_feature_research.yaml',
        help='Path to YAML/JSON research config file',
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='',
        help='Optional override for analysis output directory',
    )
    return parser.parse_args()


def main() -> None:
    """Execute feature engineering, research, regime analysis, training, and visualization."""
    args = parse_args()
    config = load_research_config(args.config)

    if args.output_dir:
        config.dataset.output_dir = args.output_dir

    output_dir = Path(config.dataset.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info('Starting quant feature research with config={}', args.config)

    dataset_pipeline = FeatureDatasetPipeline(config)
    artifacts = dataset_pipeline.build_dataset()

    analyzer = FeatureResearchAnalyzer()
    analysis_result = analyzer.analyze(
        dataset=artifacts.dataset,
        target_column=config.model.target_column,
        output_dir=config.dataset.output_dir,
    )

    regime_analyzer = RegimeAnalyzer()
    regime_result = regime_analyzer.analyze(
        dataset=artifacts.dataset,
        target_column=config.model.target_column,
        output_dir=config.dataset.output_dir,
    )

    trainer = BaselineModelTrainingPipeline(config.model)
    training_result = trainer.run(
        dataset=artifacts.dataset,
        feature_columns=artifacts.feature_columns,
        output_dir=config.dataset.output_dir,
    )

    visualizer = ResearchVisualizer()
    charts: dict[str, str] = {}
    charts['feature_importance'] = visualizer.plot_feature_importance(
        analysis_result.ranked_features,
        config.dataset.output_dir,
    )

    shap_chart = visualizer.plot_shap_importance(analysis_result.shap_importance, config.dataset.output_dir)
    if shap_chart:
        charts['shap_importance'] = shap_chart

    charts['target_distribution'] = visualizer.plot_target_distribution(
        analysis_result.target_distribution,
        config.dataset.output_dir,
    )

    regime_chart = visualizer.plot_regime_distribution(artifacts.dataset, config.dataset.output_dir)
    if regime_chart:
        charts['regime_distribution'] = regime_chart

    first_model_folds = []
    for model_name in config.model.model_types:
        fold_rows = training_result['fold_results'].get(model_name, [])
        if fold_rows:
            first_model_folds = [asdict(item) for item in fold_rows]
            break

    rolling_chart = visualizer.plot_rolling_performance(first_model_folds, config.dataset.output_dir)
    if rolling_chart:
        charts['rolling_performance'] = rolling_chart

    summary = {
        'dataset_rows': len(artifacts.dataset),
        'feature_count': len(artifacts.feature_columns),
        'target_count': len(artifacts.target_columns),
        'dataset_exports': artifacts.exports,
        'analysis_files': analysis_result.output_files,
        'regime_files': regime_result.output_files,
        'training_summary': training_result['summary'],
        'charts': charts,
    }

    summary_path = output_dir / 'quant_feature_research_summary.json'
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding='utf-8')

    logger.info('Quant feature research complete summary={}', summary_path)


if __name__ == '__main__':
    main()
