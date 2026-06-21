# backend/app/core/database.py

from contextlib import asynccontextmanager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

Engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, pool_size=20, echo=settings.DB_ECHO, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=Engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def get_async_db():
    """ Dependency to get async database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
