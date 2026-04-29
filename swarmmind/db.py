"""Database setup, schema, and health check."""

import logging
import os
import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from alembic.config import Config
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel

from alembic import command
from swarmmind.config import DATABASE_URL, DB_INIT_MODE, DB_PATH
from swarmmind.prompting import SWARMMIND_PRODUCT_IDENTITY_PROMPT

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
    """Initialize database schema using the configured initialization mode."""
    apply_schema()
    logger.info("Database initialized at %s", _get_database_url())


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
        "tasks",
        "approval_requests",
        "audit_logs",
    ]

    inspector = inspect(get_engine())
    existing = set(inspector.get_table_names())

    missing = [t for t in required_tables if t not in existing]
    if missing:
        logger.warning("Missing tables detected: %s. Auto-creating schema.", missing)
        apply_schema()
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


def seed_builtin_agent_teams() -> None:
    """Insert built-in agent team templates."""
    import json

    from sqlmodel import Session

    from swarmmind.db_models import AgentTeamTemplateDB

    builtin_teams = [
        {
            "team_id": "software-dev",
            "name": "软件开发 Team",
            "description": "覆盖需求分析、架构设计、交付规划、测试验证的完整软件交付团队",
            "icon": "💻",
            "roles": [
                {
                    "role_id": "product_expert",
                    "name": "产品专家",
                    "description": "梳理范围与优先级",
                    "default_skills": ["prd", "scope", "priority"],
                },
                {
                    "role_id": "architect",
                    "name": "架构专家",
                    "description": "识别系统边界与关键风险",
                    "default_skills": ["system_design", "risk_analysis", "tech_selection"],
                },
                {
                    "role_id": "delivery_planner",
                    "name": "交付规划专家",
                    "description": "拆里程碑和任务",
                    "default_skills": ["milestone", "task_breakdown", "estimation"],
                },
                {
                    "role_id": "test_validator",
                    "name": "测试验证专家",
                    "description": "补齐验收与风险检查",
                    "default_skills": ["test_plan", "acceptance_criteria", "risk_check"],
                },
            ],
            "default_skills": ["coding", "code_review", "documentation"],
            "runtime_profile_prefs": {"mode": "pro", "subagent_enabled": True},
        },
        {
            "team_id": "data-analysis",
            "name": "数据分析 Team",
            "description": "数据清洗、分析、报表和洞察生成的专业团队",
            "icon": "📊",
            "roles": [
                {
                    "role_id": "data_engineer",
                    "name": "数据工程师",
                    "description": "数据清洗与预处理",
                    "default_skills": ["etl", "data_cleaning"],
                },
                {
                    "role_id": "analyst",
                    "name": "分析师",
                    "description": "数据分析与可视化",
                    "default_skills": ["statistics", "visualization", "insight"],
                },
            ],
            "default_skills": ["sql", "python", "charting"],
            "runtime_profile_prefs": {"mode": "thinking", "subagent_enabled": False},
        },
        {
            "team_id": "ops-automation",
            "name": "运维自动化 Team",
            "description": "基础设施、部署流水线、监控告警和自动化脚本",
            "icon": "⚙️",
            "roles": [
                {
                    "role_id": "sre",
                    "name": "SRE",
                    "description": "可靠性工程与监控",
                    "default_skills": ["monitoring", "alerting", "incident_response"],
                },
                {
                    "role_id": "platform_engineer",
                    "name": "平台工程师",
                    "description": "基础设施与部署",
                    "default_skills": ["iac", "cicd", "containerization"],
                },
            ],
            "default_skills": ["scripting", "automation", "troubleshooting"],
            "runtime_profile_prefs": {"mode": "flash", "subagent_enabled": False},
        },
    ]

    engine = get_engine()
    with Session(engine) as session:
        for team_data in builtin_teams:
            team = AgentTeamTemplateDB(
                team_id=team_data["team_id"],
                name=team_data["name"],
                description=team_data["description"],
                icon=team_data["icon"],
                roles=json.dumps(team_data["roles"]),
                default_skills=json.dumps(team_data["default_skills"]),
                runtime_profile_prefs=json.dumps(team_data["runtime_profile_prefs"]),
                is_builtin=1,
                is_enabled=1,
            )
            session.merge(team)
        session.commit()

    logger.info("Built-in agent team templates seeded.")


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


def apply_schema() -> None:
    """Apply schema using the configured initialization mode.

    Modes:
    - ``migrate``: migration-first, suitable for real deployments.
    - ``create_all``: test/dev fallback that creates metadata directly.
    """
    mode = os.environ.get("SWARMMIND_DB_INIT_MODE", DB_INIT_MODE).strip().lower()
    if mode == "create_all":
        init_orm_db()
        return
    if mode == "migrate":
        run_migrations_to_head()
        return
    raise ValueError(f"Unsupported SWARMMIND_DB_INIT_MODE: {mode}")


def init_orm_db() -> None:
    """Initialize ORM tables (safe to call on existing DB)."""
    # Import all models so SQLModel.metadata contains every table
    from swarmmind.db_models import (  # noqa: F401
        ActionProposalDB,
        AgentDB,
        ApprovalRequestDB,
        ArtifactDB,
        AuditLogDB,
        CompactionHintDB,
        ConversationDB,
        EventLogDB,
        LlmProviderDB,
        LlmProviderModelDB,
        MemoryEntryDB,
        MessageDB,
        ProjectDB,
        RunDB,
        RuntimeModelAssignmentDB,
        RuntimeModelDB,
        SessionPromotionDB,
        SharedMemoryDB,
        StrategyChangeProposalDB,
        StrategyTableDB,
        TaskDB,
    )

    SQLModel.metadata.create_all(bind=get_engine())
    logger.info("ORM tables ensured at %s", _get_database_url())
