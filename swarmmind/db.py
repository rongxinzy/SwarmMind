"""SQLite database setup, schema, and health check."""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

from swarmmind.config import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA = """
-- Core agent registry
CREATE TABLE IF NOT EXISTS agents (
    agent_id    TEXT PRIMARY KEY,
    domain      TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Shared working memory (KV store)
CREATE TABLE IF NOT EXISTS working_memory (
    key                 TEXT PRIMARY KEY,
    value               TEXT NOT NULL,
    domain_tags         TEXT,                  -- comma-separated: 'finance,q3,acme'
    last_writer_agent_id TEXT,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Routing strategy: situation_tag -> agent_id with success tracking
CREATE TABLE IF NOT EXISTS strategy_table (
    situation_tag   TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    success_count   INTEGER DEFAULT 0,
    failure_count   INTEGER DEFAULT 0,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) DEFERRABLE INITIALLY DEFERRED
);

-- Audit log of every goal dispatch
CREATE TABLE IF NOT EXISTS event_log (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             DATETIME DEFAULT CURRENT_TIMESTAMP,
    goal                 TEXT NOT NULL,
    situation_tag         TEXT,
    dispatched_agent_id   TEXT,
    action_proposal_id    TEXT,
    supervisor_decision   TEXT,       -- 'approved' | 'rejected' | 'timeout'
    outcome              TEXT,        -- 'success' | 'failure' | 'pending'
    latency_ms           INTEGER
);

-- Action proposals from agents (pending supervisor review)
CREATE TABLE IF NOT EXISTS action_proposals (
    id              TEXT PRIMARY KEY,
    agent_id        TEXT NOT NULL,
    description     TEXT NOT NULL,
    target_resource TEXT,
    preconditions   TEXT,            -- JSON
    postconditions  TEXT,            -- JSON
    confidence      REAL DEFAULT 0.5,
    status          TEXT DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected' | 'executed'
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id) DEFERRABLE INITIALLY DEFERRED
);

-- Strategy change proposals (routing updates, human-approved)
CREATE TABLE IF NOT EXISTS strategy_change_proposals (
    id              TEXT PRIMARY KEY,
    situation_tag   TEXT NOT NULL,
    proposed_agent_id TEXT NOT NULL,
    reason          TEXT,
    status          TEXT DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
    proposed_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (proposed_agent_id) REFERENCES agents(agent_id)
);

-- Conversation sessions
CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    title_status TEXT NOT NULL DEFAULT 'pending',
    title_source TEXT,
    title_generated_at DATETIME,
    runtime_profile_id TEXT,
    runtime_instance_id TEXT,
    thread_id TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Messages within a conversation
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Layered memory entries (L4/L3/L2/L1)
CREATE TABLE IF NOT EXISTS memory_entries (
    id              TEXT PRIMARY KEY,
    layer           TEXT NOT NULL,          -- 'L4_user_soul', 'L3_project', 'L2_team', 'L1_tmp'
    scope_id        TEXT NOT NULL,          -- user_id / project_id / team_id / session_id
    key             TEXT NOT NULL,
    value           TEXT NOT NULL,
    tags            TEXT,                    -- JSON array of tag strings
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    ttl             INTEGER,                 -- seconds until expiry (NULL = no expiry)
    version         INTEGER DEFAULT 1,
    last_writer_agent_id TEXT,
    UNIQUE(layer, scope_id, key)
);

-- Session promotions: L1 → L3/L2 migration records
CREATE TABLE IF NOT EXISTS session_promotions (
    id                  TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL,
    target_layer        TEXT NOT NULL,       -- 'L3_project' or 'L2_team'
    target_scope_id     TEXT NOT NULL,
    key_filter          TEXT,                -- JSON array of keys to migrate (NULL = all)
    promoted_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
    snapshot_count      INTEGER DEFAULT 0    -- number of entries migrated
);

-- Compaction hints: Phase 2 compression policy registry
CREATE TABLE IF NOT EXISTS compaction_hints (
    id              TEXT PRIMARY KEY,
    scope_layer     TEXT NOT NULL,
    scope_id        TEXT NOT NULL,
    policy          TEXT NOT NULL,           -- 'dedup', 'compress', 'archive'
    trigger_count   INTEGER DEFAULT 0,       -- fire after N writes
    fired_at        DATETIME,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Runtime model catalog
CREATE TABLE IF NOT EXISTS runtime_models (
    name            TEXT PRIMARY KEY,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    display_name    TEXT,
    description     TEXT,
    model_class     TEXT NOT NULL,
    api_key_env_var TEXT NOT NULL,
    base_url        TEXT,
    supports_vision INTEGER NOT NULL DEFAULT 0,
    enabled         INTEGER NOT NULL DEFAULT 1,
    source          TEXT NOT NULL DEFAULT 'manual',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Subject-to-model assignment, future-proof for tenant/user/group control
CREATE TABLE IF NOT EXISTS runtime_model_assignments (
    subject_type    TEXT NOT NULL,
    subject_id      TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    is_default      INTEGER NOT NULL DEFAULT 0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (subject_type, subject_id, model_name),
    FOREIGN KEY (model_name) REFERENCES runtime_models(name) DEFERRABLE INITIALLY DEFERRED
);
"""

# Indexes for performance
INDEXES = """
CREATE INDEX IF NOT EXISTS idx_action_proposals_status ON action_proposals(status);
CREATE INDEX IF NOT EXISTS idx_event_log_timestamp ON event_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_working_memory_tags ON working_memory(domain_tags);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);
CREATE INDEX IF NOT EXISTS idx_memory_scope ON memory_entries(layer, scope_id);
CREATE INDEX IF NOT EXISTS idx_memory_layer_key ON memory_entries(layer, scope_id, key);
CREATE INDEX IF NOT EXISTS idx_memory_tags ON memory_entries(tags);
CREATE INDEX IF NOT EXISTS idx_compaction_scope ON compaction_hints(scope_layer, scope_id);
CREATE INDEX IF NOT EXISTS idx_runtime_models_enabled ON runtime_models(enabled);
CREATE INDEX IF NOT EXISTS idx_runtime_models_source ON runtime_models(source);
CREATE INDEX IF NOT EXISTS idx_runtime_model_assignments_subject ON runtime_model_assignments(subject_type, subject_id);
"""


def _get_db_path() -> str:
    """Read DB path dynamically so tests and runtime env overrides take effect."""
    return os.environ.get("SWARMMIND_DB_PATH", DB_PATH)


def _migrate_conversation_title_columns(conn: sqlite3.Connection) -> None:
    """
    Backfill newer conversation title metadata columns for existing databases.

    SQLite's CREATE TABLE IF NOT EXISTS will not alter old schemas, so we add
    missing columns here and mark legacy titled rows as already generated.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(conversations)")
    existing_columns = {row["name"] for row in cursor.fetchall()}

    if "conversations" not in {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'"
        ).fetchall()
    }:
        return

    if "title_status" not in existing_columns:
        cursor.execute(
            "ALTER TABLE conversations ADD COLUMN title_status TEXT NOT NULL DEFAULT 'pending'"
        )
    if "title_source" not in existing_columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN title_source TEXT")
    if "title_generated_at" not in existing_columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN title_generated_at DATETIME")
    if "runtime_profile_id" not in existing_columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN runtime_profile_id TEXT")
    if "runtime_instance_id" not in existing_columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN runtime_instance_id TEXT")
    if "thread_id" not in existing_columns:
        cursor.execute("ALTER TABLE conversations ADD COLUMN thread_id TEXT")

    cursor.execute(
        """
        UPDATE conversations
        SET
            title_status = CASE
                WHEN title IS NOT NULL AND TRIM(title) != '' AND title = 'New Conversation'
                    THEN 'pending'
                WHEN title IS NOT NULL AND TRIM(title) != ''
                    THEN 'generated'
                ELSE 'pending'
            END,
            title_source = CASE
                WHEN title IS NOT NULL AND TRIM(title) != '' AND title != 'New Conversation'
                    THEN COALESCE(title_source, 'legacy')
                ELSE title_source
            END,
            title_generated_at = CASE
                WHEN title IS NOT NULL AND TRIM(title) != '' AND title != 'New Conversation'
                    THEN COALESCE(title_generated_at, updated_at, created_at)
                ELSE title_generated_at
            END
        WHERE title_status IS NULL
           OR title_source IS NULL
           OR title_generated_at IS NULL
        """
    )


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Initialize database: create all tables and indexes."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Create tables
        cursor.executescript(SCHEMA)
        _migrate_conversation_title_columns(conn)
        # Create indexes
        cursor.executescript(INDEXES)
        conn.commit()
        logger.info("Database initialized at %s", _get_db_path())
    finally:
        conn.close()


def health_check() -> dict:
    """
    Verify all required tables exist.
    Auto-creates missing tables (self-healing on first boot).
    Returns dict with status.
    """
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

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        existing = {row["name"] for row in cursor.fetchall()}

        missing = [t for t in required_tables if t not in existing]
        if missing:
            logger.warning("Missing tables detected: %s. Auto-creating schema.", missing)
            cursor.executescript(SCHEMA)
            _migrate_conversation_title_columns(conn)
            cursor.executescript(INDEXES)
            conn.commit()
            return {"status": "healed", "missing_tables": missing}

        _migrate_conversation_title_columns(conn)
        cursor.executescript(INDEXES)
        conn.commit()
        return {"status": "ok", "missing_tables": []}
    finally:
        conn.close()


def seed_default_agents() -> None:
    """Insert default DeerFlow-first agent registry and routing entries."""
    conn = get_connection()
    try:
        cursor = conn.cursor()

        agents = [
            (
                "general",
                "general",
                "You are SwarmMind, an AIOS system developed by Beijing Rongxin Zhizhi Technology Co., Ltd. "
                "You are the next-generation AI Operating System, designed to assist users with "
                "intelligent task management, creative problem solving, and advanced reasoning capabilities.",
            ),
            (
                "unknown",
                "unknown",
                "Placeholder agent for legacy unmatched routing situations.",
            ),
        ]

        for agent_id, domain, system_prompt in agents:
            cursor.execute(
                "INSERT OR IGNORE INTO agents (agent_id, domain, system_prompt) VALUES (?, ?, ?)",
                (agent_id, domain, system_prompt),
            )

        # Seed initial strategy table entries
        strategies = [
            ("finance", "general"),
            ("finance_qa", "general"),
            ("quarterly_report", "general"),
            ("revenue_analysis", "general"),
            ("code_review", "general"),
            ("python_review", "general"),
            ("pr_review", "general"),
            ("unknown", "general"),
        ]

        for situation_tag, agent_id in strategies:
            cursor.execute(
                "INSERT OR IGNORE INTO strategy_table (situation_tag, agent_id) VALUES (?, ?)",
                (situation_tag, agent_id),
            )

        conn.commit()
        logger.info("Default agents seeded.")
    finally:
        conn.close()
