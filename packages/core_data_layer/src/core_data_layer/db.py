"""Compatibility wrapper around database.py."""

from core_data_layer.database import DATABASE_URL, engine, get_session, init_db

def get_sync_engine():
    return engine


__all__ = ["DATABASE_URL", "engine", "get_session", "get_sync_engine", "init_db"]
