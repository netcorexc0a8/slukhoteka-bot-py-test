"""
Database migration utilities
"""
from sqlalchemy import text
from app.database import engine, SessionLocal
import logging

logger = logging.getLogger(__name__)


def run_migration(migration_file: str):
    """
    Run a SQL migration file
    """
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()

    with SessionLocal() as db:
        try:
            db.execute(text(sql))
            db.commit()
            logger.info(f"Migration {migration_file} completed successfully")
            return True
        except Exception as e:
            db.rollback()
            logger.error(f"Migration {migration_file} failed: {e}")
            return False


def migrate():
    """
    Run all pending migrations
    """
    migrations = [
        "backend/migrations/001_add_name_to_global_users.sql",
        "backend/migrations/002_add_recurrence_and_clients.sql"
    ]

    for migration in migrations:
        logger.info(f"Running migration: {migration}")
        if not run_migration(migration):
            logger.error(f"Migration {migration} failed, stopping")
            return False

    logger.info("All migrations completed successfully")
    return True


if __name__ == "__main__":
    import sys
    success = migrate()
    sys.exit(0 if success else 1)
