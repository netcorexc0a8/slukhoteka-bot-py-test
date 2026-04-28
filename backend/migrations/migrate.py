"""
Database migration utilities.

По умолчанию каждая миграция в одной транзакции.
Маркер `-- NO_TRANSACTION` в первой строке SQL → autocommit-режим
(нужен для ALTER TYPE ... ADD VALUE и подобного DDL).
"""
import logging
import time
import traceback
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import engine, SessionLocal

logger = logging.getLogger(__name__)
MIGRATIONS_DIR = Path(__file__).parent


def _wait_for_db(max_attempts: int = 30, delay: float = 2.0) -> bool:
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database is ready")
            return True
        except OperationalError as e:
            logger.warning(f"DB not ready (attempt {attempt}/{max_attempts}): {e}")
            time.sleep(delay)
    return False


def _ensure_migrations_table():
    with SessionLocal() as db:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()


def _get_applied() -> set:
    with SessionLocal() as db:
        rows = db.execute(text("SELECT name FROM schema_migrations")).fetchall()
        return {row[0] for row in rows}


def _mark_applied(name: str):
    with SessionLocal() as db:
        db.execute(
            text("INSERT INTO schema_migrations (name) VALUES (:name) ON CONFLICT DO NOTHING"),
            {"name": name},
        )
        db.commit()


def _discover_migrations() -> list[Path]:
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def run_migration(migration_file: Path) -> bool:
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()
    no_tx = "NO_TRANSACTION" in sql.split("\n", 1)[0]
    raw_conn = engine.raw_connection()
    try:
        raw_conn.autocommit = no_tx
        cursor = raw_conn.cursor()
        try:
            cursor.execute(sql)
            if not no_tx:
                raw_conn.commit()
            logger.info(f"Migration {migration_file.name} completed successfully")
            return True
        except Exception:
            if not no_tx:
                raw_conn.rollback()
            logger.error(f"Migration {migration_file.name} failed:")
            logger.error(traceback.format_exc())
            return False
        finally:
            cursor.close()
    finally:
        raw_conn.close()


def migrate() -> bool:
    if not _wait_for_db():
        return False
    _ensure_migrations_table()
    applied = _get_applied()
    pending = [m for m in _discover_migrations() if m.name not in applied]
    if not pending:
        logger.info("No pending migrations")
        return True
    logger.info(f"Found {len(pending)} pending: {[m.name for m in pending]}")
    for m in pending:
        if not run_migration(m):
            return False
        _mark_applied(m.name)
    logger.info("All migrations applied")
    return True


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    sys.exit(0 if migrate() else 1)