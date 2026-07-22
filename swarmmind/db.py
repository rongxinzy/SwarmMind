"""Database setup, schema, and health check."""

import logging
import os
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session

from alembic import command
from swarmmind.config import DATABASE_URL, DB_PATH

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    """Read legacy DB path dynamically so tests and runtime env overrides take effect."""
    return os.environ.get("SWARMMIND_DB_PATH", DB_PATH)


def _get_database_url() -> str:
    """Return the configured SQLAlchemy URL, falling back to local SQLite path."""
    configured_url = os.environ.get("SWARMMIND_DATABASE_URL", DATABASE_URL)
    if configured_url:
        return configured_url

    path = _get_db_path()
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return f"sqlite:///{path}"


def _is_sqlite_url(database_url: str) -> bool:
    return urlparse(database_url).scheme == "sqlite"


def init_db() -> None:
    """Initialize database schema by applying Alembic migrations."""
    run_migrations_to_head()
    logger.info("Database initialized at %s", _get_database_url())


def health_check() -> dict:
    """Verify Alembic-managed schema presence and revision."""
    from sqlalchemy import inspect
    from sqlmodel import SQLModel

    import swarmmind.db_models  # noqa: F401

    required_tables = sorted({*SQLModel.metadata.tables.keys(), "alembic_version"})
    engine = get_engine()

    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    missing = [t for t in required_tables if t not in existing]
    if missing:
        logger.warning("Missing Alembic-managed tables detected: %s", missing)
        return {"status": "missing_schema", "missing_tables": missing}

    with engine.connect() as connection:
        current_revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    expected_heads = sorted(ScriptDirectory.from_config(_build_alembic_config()).get_heads())
    if current_revision not in expected_heads:
        return {
            "status": "migration_pending",
            "missing_tables": [],
            "revision": current_revision,
            "heads": expected_heads,
        }

    return {
        "status": "ok",
        "missing_tables": [],
        "revision": current_revision,
        "heads": expected_heads,
    }


_engine_lock = threading.Lock()
_engine_cache: dict[str, Engine] = {}


def _dispose_engine(engine: object) -> None:
    """Dispose an engine-like object when supported."""
    dispose = getattr(engine, "dispose", None)
    if callable(dispose):
        dispose()


def _set_sqlite_pragma(dbapi_conn, _connection_record):
    """Enable foreign keys and WAL mode for every connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


def get_engine() -> Engine:
    """Return a SQLAlchemy engine bound to the current database URL.

    Engines are cached per database URL. If the configured URL changes,
    stale cached engines are disposed before a new engine is created.
    """
    database_url = _get_database_url()
    with _engine_lock:
        cached_engine = _engine_cache.get(database_url)
        if cached_engine is not None:
            return cached_engine

        for cached_url, cached in list(_engine_cache.items()):
            if cached_url != database_url:
                _dispose_engine(cached)
                del _engine_cache[cached_url]

        engine_kwargs: dict = {
            "pool_pre_ping": True,
        }
        if _is_sqlite_url(database_url):
            engine_kwargs["connect_args"] = {"check_same_thread": False}

        engine = create_engine(
            database_url,
            **engine_kwargs,
        )
        if _is_sqlite_url(database_url):
            event.listen(engine, "connect", _set_sqlite_pragma)
        _engine_cache[database_url] = engine
        return engine


def dispose_engines() -> None:
    """Dispose all cached engines. Useful for tests and shutdown hygiene."""
    with _engine_lock:
        for engine in _engine_cache.values():
            _dispose_engine(engine)
        _engine_cache.clear()


def get_session() -> Session:
    """Return a new Session. Caller is responsible for commit/close."""
    return sessionmaker(bind=get_engine(), class_=Session, expire_on_commit=False)()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _build_alembic_config() -> Config:
    project_root = _project_root()
    alembic_ini_path = project_root / "alembic.ini"
    config = Config(str(alembic_ini_path))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", _get_database_url())
    return config


def run_migrations_to_head() -> None:
    """Apply Alembic migrations to the configured database."""
    command.upgrade(_build_alembic_config(), "head")
