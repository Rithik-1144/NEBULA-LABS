from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config.settings import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

engine = create_engine(settings.database_url.replace('sqlite+aiosqlite://', 'sqlite://'), echo=False)
async_engine = create_async_engine(
    settings.database_url.replace('sqlite://', 'sqlite+aiosqlite://')
    if settings.database_url.startswith('sqlite://')
    else settings.database_url,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
