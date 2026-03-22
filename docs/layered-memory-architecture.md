# LayeredMemory Architecture

## Overview

The LayeredMemory system provides a 4-layer scoped memory architecture that replaces the flat `working_memory` KV store with scope isolation, TTL support for temporary data, and session promotion paths.

## Layers

| Layer | Name | Scope | Purpose | TTL |
|-------|------|-------|---------|-----|
| L4 | USER_SOUL | user_id | User traits, globally unique, read-mostly | None |
| L3 | PROJECT | project_id | Project context, project-isolated | None |
| L2 | TEAM | team_id | Team memory, team-isolated | None |
| L1 | TMP | session_id | Temporary session data | 24h (default) |

**Read priority**: L1 > L2 > L3 > L4 (more specific overrides more abstract)

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Human Supervisor                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    Context Broker                            │
│  dispatch(goal, user_id, project_id, team_id, session_id) │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   MemoryContext                              │
│  { user_id, project_id, team_id, session_id }              │
│  visible_scopes = [L1, L2, L3, L4] (priority order)         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐  ┌─────────┐  ┌─────────┐
   │ Finance │  │  Code  │  │ Future  │
   │  Agent  │  │ Review │  │  Agents │
   └────┬────┘  └────┬────┘  └────┬────┘
        │             │             │
        └─────────────┼─────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   LayeredMemory                              │
│  read(key, ctx)        → priority lookup across scopes      │
│  write(scope, key, val)→ CAS or last-write-wins            │
│  promote_session(...)  → L1 → L3/L2 migration              │
│  register_compaction() → Phase 2 hint registry             │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               SQLite: memory_entries                         │
│  id, layer, scope_id, key, value, tags, ttl, version        │
│  + session_promotions, compaction_hints                       │
└─────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

### Scope Resolution
- `MemoryContext` is built at dispatch time from request parameters
- `visible_scopes` property returns layers in priority order (L1 first)
- `read(key, ctx)` iterates scopes in priority order, returns first match

### Write Authorization
- L4 (USER_SOUL) writes are restricted to agents in `SOUL_WRITER_AGENT_IDS = {"soul_writer"}`
- Regular agents attempting L4 writes raise `MemoryWriteForbidden`
- This prevents accidental corruption of user-level traits

### TTL Behavior
- L1 (TMP) entries get auto-attached TTL of 24h (`MEMORY_DEFAULT_L1_TTL_SECONDS`)
- TTL is capped at 7 days (`MEMORY_MAX_TTL_SECONDS`)
- Higher layers (L2/L3/L4) have no TTL by default
- TTL check happens at read time (lazy expiry)

### CAS Protocol
- `write()` accepts optional `expected_version` for CAS semantics
- If version mismatch detected, raises `MemoryWriteConflict`
- Without `expected_version`, uses last-write-wins with 3x retry loop

### Session Promotion
- `promote_session(session_id, target_scope, key_filter)` migrates L1 entries
- Creates a `session_promotions` record with snapshot count
- Does NOT delete source entries (Phase 2 feature)
- TTL is cleared on promotion

## Database Schema

### `memory_entries`
```sql
CREATE TABLE memory_entries (
    id              TEXT PRIMARY KEY,
    layer           TEXT NOT NULL,   -- 'L4_user_soul', 'L3_project', 'L2_team', 'L1_tmp'
    scope_id        TEXT NOT NULL,   -- user_id / project_id / team_id / session_id
    key             TEXT NOT NULL,
    value           TEXT NOT NULL,
    tags            TEXT,            -- JSON array
    created_at      DATETIME,
    updated_at      DATETIME,
    ttl             INTEGER,          -- seconds
    version         INTEGER DEFAULT 1,
    last_writer_agent_id TEXT,
    UNIQUE(layer, scope_id, key)
);
```

### `session_promotions`
```sql
CREATE TABLE session_promotions (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL,
    target_layer    TEXT NOT NULL,
    target_scope_id TEXT NOT NULL,
    key_filter      TEXT,             -- JSON array of keys
    promoted_at     DATETIME,
    snapshot_count  INTEGER DEFAULT 0
);
```

### `compaction_hints`
```sql
CREATE TABLE compaction_hints (
    id              TEXT PRIMARY KEY,
    scope_layer     TEXT NOT NULL,
    scope_id        TEXT NOT NULL,
    policy          TEXT NOT NULL,    -- 'dedup', 'compress', 'archive'
    trigger_count   INTEGER DEFAULT 0,
    fired_at        DATETIME,
    created_at      DATETIME
);
```

## API Changes

### `dispatch()` Signature
```python
def dispatch(
    goal: str,
    user_id: str = "default_user",
    project_id: str | None = None,
    team_id: str | None = None,
    session_id: str | None = None,
) -> DispatchResponse:
    # Returns MemoryContext in response.memory_ctx
```

### `BaseAgent.act()` Signature
```python
def act(
    self,
    goal: str,
    action_proposal_id: str,
    ctx: MemoryContext | None = None,  # NEW: MemoryContext parameter
) -> ActionProposal:
```

## Configuration

```python
# config.py
MEMORY_DEFAULT_L1_TTL_SECONDS = 86400  # 24 hours
MEMORY_MAX_TTL_SECONDS = 604800       # 7 days
SOUL_WRITER_AGENT_IDS = {"soul_writer"}
```

## Phase 2 (Out of Scope)

- Data migration from `working_memory` to `memory_entries`
- Compaction execution (agent reads hints table, performs compression)
- Embedding-based routing (replacing keyword routing)
- L1 source entry deletion after promotion
