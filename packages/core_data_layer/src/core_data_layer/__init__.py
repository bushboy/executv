"""Shared PostgreSQL data layer for ExecuTV."""

from core_data_layer.database import engine, get_session, init_db

__version__ = "0.1.0"

__all__ = ["engine", "get_session", "init_db"]
