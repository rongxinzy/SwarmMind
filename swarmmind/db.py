"""SQLite database setup, schema, and health check."""

import logging
import os

from swarmmind.config import DB_PATH
from swarmmind.prompting import SWARMMIND_PRODUCT_IDENTITY_PROMPT

logger = logging.getLogger(__name__)


def _get_db_path() -> str:
    """Read DB path dynamically so tests and runtime env overrides take effect."""
    return os.environ.get("SWARMMIND_DB_PATH", DB_PATH)


def init_db() -> None:
    """Initialize database: create all tables and indexes."""
    init_orm_db()
    logger.info("Database initialized at %s", _get_db_path())


def health_check() -> dict:
    """Verify all required tables exist.
    Auto-creates missing tables (self-healing on first boot).
    Returns dict with status.
    """
    from sqlalchemy import inspect

    required_tables = [
        "agents",
        "working_memory",
        "strategy_table",
        "event_log",
        "action_proposals",
        "strategy_change_proposals",
        "conversations",
        "messages",
        "memory_entries",
        "session_promotions",
        "compaction_hints",
        "runtime_models",
        "runtime_model_assignments",
    ]

    inspector = inspect(get_engine())
    existing = set(inspector.get_table_names())

    missing = [t for t in required_tables if t not in existing]
    if missing:
        logger.warning("Missing tables detected: %s. Auto-creating schema.", missing)
        init_orm_db()
        return {"status": "healed", "missing_tables": missing}

    return {"status": "ok", "missing_tables": []}


def seed_default_agents() -> None:
    """Insert default DeerFlow-first agent registry and routing entries."""
    from sqlmodel import Session

    from swarmmind.db_models import AgentDB, StrategyTableDB

    engine = get_engine()
    with Session(engine) as session:
        agents = [
            AgentDB(
                agent_id="general",
                domain="general",
                system_prompt=SWARMMIND_PRODUCT_IDENTITY_PROMPT,
            ),
            AgentDB(
                agent_id="unknown",
                domain="unknown",
                system_prompt="Placeholder agent for legacy unmatched routing situations.",
            ),
        ]
        for agent in agents:
            session.merge(agent)

        strategies = [
            StrategyTableDB(situation_tag="finance", agent_id="general"),
            StrategyTableDB(situation_tag="finance_qa", agent_id="general"),
            StrategyTableDB(situation_tag="quarterly_report", agent_id="general"),
            StrategyTableDB(situation_tag="revenue_analysis", agent_id="general"),
            StrategyTableDB(situation_tag="code_review", agent_id="general"),
            StrategyTableDB(situation_tag="python_review", agent_id="general"),
            StrategyTableDB(situation_tag="pr_review", agent_id="general"),
            StrategyTableDB(situation_tag="unknown", agent_id="general"),
        ]
        for strategy in strategies:
            session.merge(strategy)

        session.commit()

    logger.info("Default agents seeded.")


# ---------------------------------------------------------------------------
# ORM layer (SQLModel / SQLAlchemy 2.0)
# ---------------------------------------------------------------------------

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel


def _get_db_url() -> str:
    """Return SQLAlchemy-compatible SQLite URL."""
    path = _get_db_path()
    # Use absolute path to avoid cwd issues in alembic
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    return f"sqlite:///{path}"


def _set_sqlite_pragma(dbapi_conn, _connection_record):
    """Enable foreign keys and WAL mode for every connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.close()


def get_engine() -> "sqlalchemy.engine.Engine":
    """Return a SQLAlchemy engine bound to the current DB path.

    NOTE: A new engine is created on every call so that tests which
    override SWARMMIND_DB_PATH get the correct database without stale
    singleton state.
    """
    engine = create_engine(
        _get_db_url(),
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    event.listen(engine, "connect", _set_sqlite_pragma)
    return engine


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


def init_orm_db() -> None:
    """Initialize ORM tables (safe to call on existing DB)."""
    # Import all models so SQLModel.metadata contains every table
    from swarmmind.db_models import (  # noqa: F401
        ActionProposalDB,
        AgentDB,
        CompactionHintDB,
        ConversationDB,
        EventLogDB,
        MemoryEntryDB,
        MessageDB,
        RuntimeModelAssignmentDB,
        RuntimeModelDB,
        SessionPromotionDB,
        StrategyChangeProposalDB,
        StrategyTableDB,
        WorkingMemoryDB,
    )

    SQLModel.metadata.create_all(bind=get_engine())
    logger.info("ORM tables ensured at %s", _get_db_path())
