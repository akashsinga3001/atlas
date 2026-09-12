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
    "code": "nifty_iron_condor",
    "name": "NIFTY Iron Condor",
    "version": 2,
    "implementation_class": "nifty_iron_condor",
    "exit_evaluator_class": None,
    "execution_engine": "options_iron_condor",
    "config": {
        # PAPER TRADING — live_trading_enabled defaults to False. Entries/exits simulate
        # fills against live quotes instead of placing real Kite orders until this is
        # deliberately flipped after a reviewed paper-trading period. See
        # OptionsTradeService's class docstring for exactly what that gate does.
        "live_trading_enabled": False,
        "underlying_ticker": "NIFTY 50",
        "option_name": "NIFTY",
        "vix_ticker": "INDIA VIX",
        "entry_dte_target": 35,
        "short_delta_target": 0.20,
        "delta_tolerance": 0.05,
        "wing_width_points": 400,
        "profit_target_pct": 0.50,
        "stop_loss_multiple": 2.0,
        "time_exit_dte": 7,
        "vix_percentile_lookback_days": 252,
        "vix_avoid_band_low": 33,
        "vix_avoid_band_high": 67,
        "max_lots": 50,
        "risk_free_rate": 0.065,
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
