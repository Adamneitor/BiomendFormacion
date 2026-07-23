"""
Conexión a PostgreSQL para BIOMEND Formación Continua.
Si DATABASE_URL no está definida, la app opera en modo sin BDD (fallback TSV).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def normalize_database_url(url: str) -> str:
    """
    Normaliza URLs de Railway/Heroku (postgres://) al dialecto SQLAlchemy + psycopg3.
    """
    cleaned = url.strip()
    if cleaned.startswith("postgres://"):
        cleaned = "postgresql://" + cleaned[len("postgres://") :]
    if cleaned.startswith("postgresql+psycopg://"):
        return cleaned
    if cleaned.startswith("postgresql://"):
        cleaned = "postgresql+psycopg://" + cleaned[len("postgresql://") :]
    return cleaned


@lru_cache(maxsize=1)
def get_database_url() -> Optional[str]:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if not url:
        return None
    return normalize_database_url(url)


@lru_cache(maxsize=1)
def get_engine() -> Optional[Engine]:
    url = get_database_url()
    if not url:
        return None
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


def database_enabled() -> bool:
    return get_engine() is not None


def ping_database() -> bool:
    engine = get_engine()
    if engine is None:
        return False
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
