"""
Aplica migraciones SQL al arrancar (idempotente).
La estructura vive en db/migrations/ — Railway arranca vacío hasta ejecutar esto.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger("biomend.migrate")

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "db" / "migrations"


def _split_sql(sql: str) -> list[str]:
    """Parte el script en statements (sin bloques $$)."""
    parts: list[str] = []
    buf: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buf.append(line)
        if ";" in line:
            chunk = "\n".join(buf)
            for stmt in chunk.split(";"):
                stmt = stmt.strip()
                if stmt:
                    parts.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        parts.append(tail)
    # Filtrar vacíos residuales
    return [p for p in parts if p and not re.fullmatch(r"\s*", p)]


def apply_migrations(engine: Engine) -> None:
    if engine is None:
        return
    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not sql_files:
        logger.warning("No hay archivos SQL en %s", MIGRATIONS_DIR)
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS biomend_schema_migrations (
                    filename TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        applied = {
            row[0]
            for row in conn.execute(text("SELECT filename FROM biomend_schema_migrations")).fetchall()
        }
        for path in sql_files:
            if path.name in applied:
                continue
            logger.info("Aplicando migración %s", path.name)
            sql = path.read_text(encoding="utf-8")
            for stmt in _split_sql(sql):
                conn.execute(text(stmt))
            conn.execute(
                text("INSERT INTO biomend_schema_migrations (filename) VALUES (:f)"),
                {"f": path.name},
            )
            logger.info("Migración %s aplicada", path.name)
