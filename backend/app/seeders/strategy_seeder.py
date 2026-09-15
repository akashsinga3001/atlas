# backend/app/seeders/strategy_seeder.py

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.strategy import Strategy, StrategyVersion
from app.utils.logger import get_logger

logger = get_logger(__name__)

STRATEGIES = [{
    "code": "dummy",
    "name": "Dummy Strategy",
    "version": 1,
    "implementation_class": "dummy",
    "exit_evaluator_class": None,
    "execution_engine": "equity",
    "config": {}
}, {
    "code": "momentum_screener",
    "name": "Momentum Screener",
    "version": 1,
    "implementation_class": "momentum_screener",
    "exit_evaluator_class": "atr_trailing_stop",
    "execution_engine": "equity",
    "config": {
        "setup": {
            "quantiles": {
                "ema_compression": 0.90,
                "close_near_high": 0.80
            }
        },
        "selection": {
            "max_signals": 4,
            "sort_by": "ticker",
            "ascending": True
        },
        "entry": {
            "price": "close"
        },
        "exit": {
            "atr_trailing_stop": {
                "enabled": True,
                "atr_period": 14,
                "atr_multiple": 5.0,
                "trailing_basis": "highest_close"
            },
            "timeout": {
                "enabled": True,
                "days": 60
            }
        }
    }
}, {
    "code": "relative_leadership_v1",
    "name": "Relative Leadership V1",
    "version": 1,
    "implementation_class": "relative_leadership_v1",
    "exit_evaluator_class": "relative_leadership_deterioration",
    "execution_engine": "equity",
    "config": {
        # Frozen per relative_leadership_v1_strategy_spec.md — see RelativeLeadershipV1Config's
        # docstring. Not meant to be tuned via the UI; changing any of these values defines a
        # new strategy version, not an edit to this one.
        "signal": {
            "momentum_recent_offset": 21,
            "momentum_lookback_offset": 126,
            "entry_percentile": 0.10
        },
        "selection": {
            "max_signals": 20
        },
        "exit": {
            "relative_leadership_deterioration": {
                "outside_percentile": 0.30,
                "confirmation_sessions": 3
            }
        },
        "execution": {
            "entry_price_source": "open",
            "stop_loss_enabled": False,
            "max_hold_days": None
        },
        "account_capital_pct": 1.0
    }
}]


def seed_strategy(db: Session, *, code: str, name: str, version: int, implementation_class: str, exit_evaluator_class: str | None, execution_engine: str, config: dict) -> None:
    strategy = db.query(Strategy).filter(Strategy.code == code).first()

    if strategy is None:
        strategy = Strategy(code=code, name=name, is_active=True, execution_engine=execution_engine)
        db.add(strategy)
        db.flush()

    strategy_version = db.query(StrategyVersion).filter(StrategyVersion.strategy_id == strategy.id, StrategyVersion.version == version).first()

    if strategy_version is None:
        strategy_version = StrategyVersion(strategy_id=strategy.id, version=version, implementation_class=implementation_class, exit_evaluator_class=exit_evaluator_class, config=config, is_active=True)
        db.add(strategy_version)

    db.commit()


def seed() -> None:
    """ Seed strategies into the database."""
    db = SessionLocal()
    try:
        for strategy in STRATEGIES:
            seed_strategy(db, **strategy)
        logger.info("Seeded strategies into the database.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
