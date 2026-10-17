"""PostgreSQL engine and session generator for ExecuTV."""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from core_data_layer.config import get_settings

_settings = get_settings()
DATABASE_URL = _settings.sync_database_url

engine = create_engine(DATABASE_URL, echo=_settings.sql_echo, pool_pre_ping=True)


def init_db() -> None:
    """Create tables. Import models first so SQLModel metadata is complete."""
    from core_data_layer import models as _models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
