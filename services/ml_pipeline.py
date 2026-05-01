"""End-to-end orchestration for ML training, inference, reporting, and email delivery."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

from config import settings
from models.ml import MlPrediction, MlReport, MlTrainingRun
from services.emailer import EmailService
from services.ml_dataset import MlDatasetService
from services.ml_model import MlModelService
from services.ml_report import MlReportService
from utils.logger import logger


class MlPipelineService:
    """Coordinates weekly retraining and daily prediction/report pipeline."""

    def __init__(self) -> None:
        self._engine = create_engine(settings.DATABASE_URL, echo=settings.DB_ECHO, future=True)
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, future=True)

        self._dataset_service = MlDatasetService()
        self._model_service = MlModelService()
        self._report_service = MlReportService()
        self._email_service = EmailService()

    def run_weekly_training(self, run_date: date | None = None) -> dict[str, Any]:
        """Build weekly dataset, train long/short models, and persist metadata."""
        effective_date = run_date or date.today()
        threshold_pct = float(settings.ML_MOVE_THRESHOLD_PCT)
        horizon_days = int(settings.ML_HORIZON_DAYS)

        logger.info('ML weekly training started run_date={} threshold_pct={} horizon_days={}', effective_date, threshold_pct, horizon_days)

        dataset = self._dataset_service.build_training_dataset(horizon_days=horizon_days, threshold_pct=threshold_pct)
        if len(dataset.records) < settings.ML_MIN_TRAIN_SAMPLES:
            raise ValueError(f'Insufficient training records: {len(dataset.records)} < {settings.ML_MIN_TRAIN_SAMPLES}')

        trained = self._model_service.train(
            run_date=effective_date,
            records=dataset.records,
            feature_keys=dataset.feature_keys,
        )

        run_id = self._upsert_training_run(
            run_date=effective_date,
            horizon_days=horizon_days,
            threshold_pct=threshold_pct,
            trained=trained,
            notes=None,
        )

        logger.info('ML weekly training completed run_id={} samples_total={}', run_id, trained.samples_total)

        return {
            'success': True,
            'training_run_id': run_id,
            'run_date': effective_date.isoformat(),
            'samples_total': trained.samples_total,
            'samples_train': trained.samples_train,
            'samples_validation': trained.samples_validation,
            'long_metrics': trained.long_metrics,
            'short_metrics': trained.short_metrics,
            'long_model_path': trained.long_model_path,
            'short_model_path': trained.short_model_path,
        }

    def run_daily_inference(self, report_date: date | None = None, send_email: bool = True) -> dict[str, Any]:
        """Run daily scoring, persist predictions, generate HTML report, and optionally send email."""
        effective_date = report_date or date.today()
        threshold_pct = float(settings.ML_MOVE_THRESHOLD_PCT)
        horizon_days = int(settings.ML_HORIZON_DAYS)
        top_n = int(settings.ML_TOP_N_PER_DIRECTION)

        training_run = self._latest_successful_training_run()
        if training_run is None:
            raise ValueError('No successful training run available for inference')

        logger.info('ML daily inference started report_date={} using_training_run_id={}', effective_date, training_run.id)

        dataset = self._dataset_service.build_inference_dataset()
        if not dataset.records:
            raise ValueError('No inference records available for scoring')

        data_as_of_date = max(record['prediction_date'] for record in dataset.records)
        fresh_records = [record for record in dataset.records if record['prediction_date'] == data_as_of_date]

        long_predictions = self._model_service.score_direction(
            records=fresh_records,
            feature_keys=dataset.feature_keys,
            model_path=training_run.long_model_path,
            direction='long',
            top_n=top_n,
        )
        short_predictions = self._model_service.score_direction(
            records=fresh_records,
            feature_keys=dataset.feature_keys,
            model_path=training_run.short_model_path,
            direction='short',
            top_n=top_n,
        )

        self._upsert_predictions(training_run.id, effective_date, long_predictions, horizon_days, threshold_pct)
        self._upsert_predictions(training_run.id, effective_date, short_predictions, horizon_days, threshold_pct)

        top_long = [row for row in long_predictions if row.get('rank') is not None][:top_n]
        top_short = [row for row in short_predictions if row.get('rank') is not None][:top_n]
        safe_top_long = self._json_safe_value(top_long)
        safe_top_short = self._json_safe_value(top_short)

        subject = f'Atlas ML Signals - {effective_date.isoformat()}'
        html_body = self._report_service.build_html(
            report_date=effective_date,
            horizon_days=horizon_days,
            threshold_pct=threshold_pct,
            top_long=top_long,
            top_short=top_short,
            long_feature_importance=training_run.long_feature_importance,
            short_feature_importance=training_run.short_feature_importance,
            training_metrics={'long': training_run.long_metrics, 'short': training_run.short_metrics},
        )

        report_id = self._upsert_report(
            training_run_id=training_run.id,
            report_date=effective_date,
            email_to=settings.ML_REPORT_RECIPIENT,
            subject=subject,
            html_body=html_body,
            top_long=safe_top_long,
            top_short=safe_top_short,
            status='generated',
            sent_at=None,
        )

        email_sent = False
        if send_email:
            self._email_service.send_html(settings.ML_REPORT_RECIPIENT, subject, html_body)
            email_sent = True
            self._upsert_report(
                training_run_id=training_run.id,
                report_date=effective_date,
                email_to=settings.ML_REPORT_RECIPIENT,
                subject=subject,
                html_body=html_body,
                top_long=safe_top_long,
                top_short=safe_top_short,
                status='sent',
                sent_at=datetime.utcnow(),
            )

        logger.info('ML daily inference completed report_id={} long_candidates={} short_candidates={} email_sent={}', report_id, len(top_long), len(top_short), email_sent)

        return {
            'success': True,
            'training_run_id': training_run.id,
            'report_id': report_id,
            'report_date': effective_date.isoformat(),
            'data_as_of_date': data_as_of_date.isoformat(),
            'email_sent': email_sent,
            'email_to': settings.ML_REPORT_RECIPIENT,
            'top_long': safe_top_long,
            'top_short': safe_top_short,
        }

    def _upsert_training_run(
        self,
        run_date: date,
        horizon_days: int,
        threshold_pct: float,
        trained: Any,
        notes: str | None,
    ) -> int:
        """Upsert weekly training run row keyed by run_date."""
        statement = insert(MlTrainingRun).values(
            run_date=run_date,
            status='completed',
            universe='EQ',
            horizon_days=horizon_days,
            threshold_pct=Decimal(str(round(threshold_pct, 4))),
            samples_total=trained.samples_total,
            samples_train=trained.samples_train,
            samples_validation=trained.samples_validation,
            long_positive_rate_pct=Decimal(str(round(trained.long_positive_rate_pct, 4))),
            short_positive_rate_pct=Decimal(str(round(trained.short_positive_rate_pct, 4))),
            long_metrics=trained.long_metrics,
            short_metrics=trained.short_metrics,
            feature_columns=trained.feature_columns,
            feature_statistics=trained.feature_statistics,
            long_feature_importance=trained.long_feature_importance,
            short_feature_importance=trained.short_feature_importance,
            long_model_path=trained.long_model_path,
            short_model_path=trained.short_model_path,
            notes=notes,
        )

        upsert_statement = statement.on_conflict_do_update(
            constraint='uq_ml_training_runs_run_date',
            set_={
                'status': statement.excluded.status,
                'universe': statement.excluded.universe,
                'horizon_days': statement.excluded.horizon_days,
                'threshold_pct': statement.excluded.threshold_pct,
                'samples_total': statement.excluded.samples_total,
                'samples_train': statement.excluded.samples_train,
                'samples_validation': statement.excluded.samples_validation,
                'long_positive_rate_pct': statement.excluded.long_positive_rate_pct,
                'short_positive_rate_pct': statement.excluded.short_positive_rate_pct,
                'long_metrics': statement.excluded.long_metrics,
                'short_metrics': statement.excluded.short_metrics,
                'feature_columns': statement.excluded.feature_columns,
                'feature_statistics': statement.excluded.feature_statistics,
                'long_feature_importance': statement.excluded.long_feature_importance,
                'short_feature_importance': statement.excluded.short_feature_importance,
                'long_model_path': statement.excluded.long_model_path,
                'short_model_path': statement.excluded.short_model_path,
                'notes': statement.excluded.notes,
                'updated_at': statement.excluded.updated_at,
            },
        ).returning(MlTrainingRun.id)

        with self._session_factory() as session:
            run_id = int(session.execute(upsert_statement).scalar_one())
            session.commit()
            return run_id

    def _upsert_predictions(
        self,
        training_run_id: int,
        prediction_date: date,
        predictions: list[dict[str, Any]],
        horizon_days: int,
        threshold_pct: float,
    ) -> None:
        """Bulk upsert directional prediction rows for one date."""
        if not predictions:
            return

        rows = []
        for row in predictions:
            rows.append(
                {
                    'training_run_id': training_run_id,
                    'security_id': row['security_id'],
                    'prediction_date': prediction_date,
                    'ticker': row['ticker'],
                    'direction': row['direction'],
                    'confidence': Decimal(str(round(float(row['confidence']), 6))),
                    'rank': row['rank'],
                    'horizon_days': horizon_days,
                    'threshold_pct': Decimal(str(round(threshold_pct, 4))),
                    'top_features': row.get('top_features', []),
                }
            )

        statement = insert(MlPrediction).values(rows)
        upsert_statement = statement.on_conflict_do_update(
            constraint='uq_ml_predictions_date_security_direction',
            set_={
                'training_run_id': statement.excluded.training_run_id,
                'ticker': statement.excluded.ticker,
                'confidence': statement.excluded.confidence,
                'rank': statement.excluded.rank,
                'horizon_days': statement.excluded.horizon_days,
                'threshold_pct': statement.excluded.threshold_pct,
                'top_features': statement.excluded.top_features,
                'updated_at': statement.excluded.updated_at,
            },
        )

        with self._session_factory() as session:
            session.execute(upsert_statement)
            session.commit()

    def _upsert_report(
        self,
        training_run_id: int,
        report_date: date,
        email_to: str,
        subject: str,
        html_body: str,
        top_long: list[dict[str, Any]],
        top_short: list[dict[str, Any]],
        status: str,
        sent_at: datetime | None,
    ) -> int:
        """Upsert report row keyed by report_date and return report id."""
        statement = insert(MlReport).values(
            training_run_id=training_run_id,
            report_date=report_date,
            email_to=email_to,
            subject=subject,
            status=status,
            top_long=top_long,
            top_short=top_short,
            html_body=html_body,
            sent_at=sent_at,
        )

        upsert_statement = statement.on_conflict_do_update(
            constraint='uq_ml_reports_report_date',
            set_={
                'training_run_id': statement.excluded.training_run_id,
                'email_to': statement.excluded.email_to,
                'subject': statement.excluded.subject,
                'status': statement.excluded.status,
                'top_long': statement.excluded.top_long,
                'top_short': statement.excluded.top_short,
                'html_body': statement.excluded.html_body,
                'sent_at': statement.excluded.sent_at,
                'updated_at': statement.excluded.updated_at,
            },
        ).returning(MlReport.id)

        with self._session_factory() as session:
            report_id = int(session.execute(upsert_statement).scalar_one())
            session.commit()
            return report_id

    def _latest_successful_training_run(self) -> MlTrainingRun | None:
        """Return latest completed training run for inference usage."""
        with self._session_factory() as session:
            query = (
                select(MlTrainingRun)
                .where(MlTrainingRun.status == 'completed')
                .order_by(MlTrainingRun.run_date.desc(), MlTrainingRun.id.desc())
            )
            return session.execute(query).scalars().first()

    def _json_safe_value(self, value: Any) -> Any:
        """Recursively normalize values for JSON column persistence."""
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, dict):
            return {key: self._json_safe_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._json_safe_value(item) for item in value]
        return value
