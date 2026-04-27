"""
Database migration utilities.

Idempotent: запоминает применённые миграции в таблице schema_migrations,
повторный запуск пропускает уже накаченное.

Порядок запуска: все *.sql файлы в backend/migrations/, отсортированные по имени.
Поэтому миграции должны иметь префикс с порядковым номером (001_, 002_, 003_, ...).
"""
import logging
import time
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.database import engine, SessionLocal

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent  # backend/migrations/


def _wait_for_db(max_attempts: int = 30, delay: float = 2.0) -> bool:
    """Ждём, пока БД станет доступна (на случай, если контейнер БД ещё стартует)."""
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database is ready")
            return True
        except OperationalError as e:
            logger.warning(f"DB not ready (attempt {attempt}/{max_attempts}): {e}")
            time.sleep(delay)
    logger.error("Database is not available after waiting")
    return False


def _ensure_migrations_table():
    """Создаёт таблицу schema_migrations, если её ещё нет."""
    with SessionLocal() as db:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name VARCHAR(255) PRIMARY KEY,
                applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()


def _get_applied() -> set:
    """Возвращает множество имён уже применённых миграций."""
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
    """Все *.sql миграции, отсортированные по имени."""
    return sorted(MIGRATIONS_DIR.glob("*.sql"))


def run_migration(migration_file: Path) -> bool:
    """Накатывает одну SQL-миграцию. Откатывается при ошибке."""
    with open(migration_file, "r", encoding="utf-8") as f:
        sql = f.read()

    with SessionLocal() as db:
        try:
            db.execute(text(sql))
            db.commit()
            logger.info(f"Migration {migration_file.name} completed successfully")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Migration {migration_file.name} failed: {e}")
            return False


def migrate() -> bool:
    """Прогоняет все ещё не применённые миграции в порядке имён."""
    if not _wait_for_db():
        return False

    _ensure_migrations_table()
    applied = _get_applied()
    migrations = _discover_migrations()

    if not migrations:
        logger.warning(f"No migrations found in {MIGRATIONS_DIR}")
        return True

    pending = [m for m in migrations if m.name not in applied]
    if not pending:
        logger.info("No pending migrations")
        return True

    logger.info(f"Found {len(pending)} pending migration(s): {[m.name for m in pending]}")

    for migration in pending:
        logger.info(f"Running migration: {migration.name}")
        if not run_migration(migration):
            logger.error(f"Migration {migration.name} failed, stopping")
            return False
        _mark_applied(migration.name)

    logger.info("All migrations applied")
    return True


if __name__ == "__main__":
    import sys
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    success = migrate()
    sys.exit(0 if success else 1)
