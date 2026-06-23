# backend/app/seeders/strategy_seeder.py

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.strategy import Strategy, StrategyVersion
from app.utils.logger import get_logger

logger = get_logger(__name__)

STRATEGIES = [{ "code": "dummy", "name": "Dummy Strategy", "version": 1, "implementation_class": "dummy", "config": {} }, { "code": "momentum_screener", "name": "Momentum Screener", "version": 1, "implementation_class": "momentum_screener", "config": {}, }]


def seed_strategy(db: Session, *, code: str, name: str, version: int, implementation_class: str, config: dict) -> None:
    """ Seed a strategy into the database."""
    strategy = db.query(Strategy).filter(Strategy.code == code).first()

    if strategy is None:
        strategy = Strategy(code=code, name=name, is_active=True)
        db.add(strategy)
        db.flush()

    strategy_version = db.query(StrategyVersion).filter(StrategyVersion.strategy_id == strategy.id, StrategyVersion.version == version).first()

    if strategy_version is None:
        strategy_version = StrategyVersion(strategy_id=strategy.id, version=version, implementation_class=implementation_class, config=config, is_active=True)
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
