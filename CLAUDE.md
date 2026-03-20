# SwarmMind — CLAUDE.md

**AI agent team operating system. Phase 1 in progress.**

## Project Overview

SwarmMind is an **operating system for AI agent teams** — agents collaborate via shared context (not message passing), humans supervise, and the team self-evolves via strategy tables.

- **Repo**: https://github.com/rongxinzy/SwarmMind
- **Status**: Phase 1 — building minimal working system
- **Frontend**: shadcn/ui (React + Tailwind CSS)
- **Backend**: Python (FastAPI or Flask TBD)
- **Storage**: SQLite (Phase 1)

## Architecture

```
Human Supervisor
       │
       ▼
┌──────────────────┐     ┌─────────────────────────────┐
│   Supervisor UI  │     │     Context Broker         │
│   (shadcn/ui)    │ ←── │  routes goals → agents     │
└──────────────────┘     └──────────┬──────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
       ┌────────────┐       ┌────────────┐       ┌────────────┐
       │  Finance   │       │   Code     │       │  Future    │
       │   Agent    │       │  Review    │       │   Agents   │
       └────────────┘       └────────────┘       └────────────┘
              │                     │                     │
              └─────────────────────┴─────────────────────┘
                                    │
                          ┌─────────────────┐
                          │  Shared Context │  ← SQLite KV store
                          │  (working_memory)│
                          └─────────────────┘
```

## Code Structure (Phase 1)

```
swarmmind/
├── CLAUDE.md              ← 你在这里
├── README.md
├── README_zh.md
├── requirements.txt
├── swarmmind/
│   ├── __init__.py
│   ├── db.py              # SQLite schema, init, health check
│   ├── models.py          # Pydantic/dataclass models
│   ├── context_broker.py  # dispatch(), route, strategy table
│   ├── shared_memory.py    # KV store with 409 conflict retry
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py        # BaseAgent class
│   │   ├── finance.py     # Finance Q&A agent
│   │   └── code_review.py # Code review agent
│   ├── api/
│   │   ├── __init__.py
│   │   └── supervisor.py  # Supervisor REST API (FastAPI)
│   ├── renderer.py         # LLM Status Renderer
│   └── config.py           # Settings, LLM config, DB path
├── ui/                    # Supervisor web UI (shadcn/ui)
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── components/
│   └── tailwind.config.js
└── tests/
    ├── test_dispatch.py
    ├── test_agents.py
    ├── test_shared_memory.py
    └── test_api.py
```

## Phase 1 Implementation Checklist

- [x] README (English + Chinese)
- [ ] SQLite schema + health check (db.py)
- [ ] Models (models.py)
- [ ] SharedMemory with 409 retry (shared_memory.py)
- [ ] ContextBroker + dispatch() + keyword routing (context_broker.py)
- [ ] Finance Agent (agents/finance.py)
- [ ] Code Review Agent (agents/code_review.py)
- [ ] Supervisor API (api/supervisor.py)
  - GET  /pending
  - POST /approve/{id}
  - POST /reject/{id}
  - GET  /status?goal=...
  - GET  /strategy
  - POST /strategy/approve/{change_id}
- [ ] LLM Status Renderer (renderer.py)
- [ ] Supervisor UI (ui/) — **shadcn/ui**
- [ ] Strategy table logic
- [ ] Action proposal timeout (5 min)
- [ ] Core tests

## Key Design Decisions

- **No auth in Phase 1** — supervisor API is localhost-only
- **Keyword routing** — Phase 1 placeholder; Phase 2 → embedding-based
- **Last-write-wins** — shared memory conflict resolution
- **No pagination on event_log** — Phase 1 scale is small
- **Logging only** — no strict LLM response validation
- **SQLite** — Phase 1 storage; swap-ready via abstraction

## LLM Configuration

Set via environment variables:
```bash
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
```

## Database

SQLite at `./swarmmind.db` (configurable via `SWARMMIND_DB_PATH`).

## Important Notes

- **ui/** is a separate React app (shadcn/ui + Tailwind)
- API runs on port 8000 by default
- Supervisor UI polls `/pending` every 5 seconds
- Action proposals time out in 5 minutes if not approved/rejected
- Strategy table updates require supervisor approval (human-in-the-loop)

## Context Broker Routing Rules (Phase 1)

| Keyword in goal | Routes to |
|----------------|-----------|
| "finance", "financial", "Q3", "quarterly", "revenue" | Finance Agent |
| "code", "review", "PR", "git", "python", "bug" | Code Review Agent |
| (no match) | Returns error, logs situation_tag="unknown" |

## Related Docs

- `/Users/krli/workspace/SwarmMind/README.md` — public-facing README
- `/Users/krli/workspace/SwarmMind/README_zh.md` — Chinese README
- `/Users/krli/.gstack/projects/rx-opensource-team/krli-main-design-20260320-224059.md` — full design doc
