# SwarmMind — CLAUDE.md

**AI agent team operating system. Phase 1 in progress.**

## Project Overview

SwarmMind is an **operating system for AI agent teams** — agents collaborate via shared context (not message passing), humans supervise, and the team self-evolves via strategy tables.

- **Repo**: https://github.com/rongxinzy/SwarmMind
- **Status**: Phase 1 — building minimal working system
- **Frontend**: shadcn/ui (React 18 + Tailwind CSS + Vite)
- **Backend**: Python (FastAPI)
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

## Code Structure

```
swarmmind/
├── CLAUDE.md              ← 你在这里
├── README.md               ← 英文 README (badges, tables, hero)
├── README_zh.md           ← 中文 README
├── requirements.txt
├── swarmmind/
│   ├── __init__.py
│   ├── __version__ = "0.1.0"
│   ├── config.py           ✅ Settings (LLM, DB, timeouts)
│   ├── db.py               ✅ SQLite schema + health check + seed
│   ├── models.py           ✅ Pydantic models (all 6 tables)
│   ├── context_broker.py   ✅ dispatch(), keyword routing, strategy table
│   ├── shared_memory.py    ✅ KV store, last-write-wins, 409 retry
│   ├── renderer.py         ✅ LLM Status Renderer (prose only)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py         ✅ BaseAgent with LLM call + error handling
│   │   ├── finance.py      ✅ FinanceAgent
│   │   └── code_review.py  ✅ CodeReviewAgent
│   └── api/
│       ├── __init__.py
│       └── supervisor.py   ✅ FastAPI supervisor REST API
├── ui/                    ✅ Supervisor web UI
│   ├── package.json        ✅ Vite + React 18 + Tailwind + shadcn deps
│   ├── vite.config.ts
│   ├── tailwind.config.js  ✅ shadcn/ui theme variables
│   ├── postcss.config.js
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx         ✅ Full supervisor UI (proposals + strategy + status)
│       ├── index.css       ✅ Tailwind + shadcn CSS variables
│       └── lib/
│           └── utils.ts    ✅ cn() utility
└── tests/
    ├── __init__.py
    ├── test_dispatch.py     ✅ dispatch, routing, strategy table tests
    └── test_shared_memory.py ✅ KV store tests
```

## Phase 1 Implementation Checklist

- [x] README (English + Chinese, badges, tables)
- [x] CLAUDE.md
- [x] SQLite schema + health check (db.py)
- [x] Models (models.py)
- [x] SharedMemory with 409 retry (shared_memory.py)
- [x] ContextBroker + dispatch() + keyword routing (context_broker.py)
- [x] Finance Agent (agents/finance.py)
- [x] Code Review Agent (agents/code_review.py)
- [x] Supervisor API (api/supervisor.py)
  - GET  /pending (paginated ✅)
  - POST /approve/{id}
  - POST /reject/{id}
  - GET  /status?goal=...
  - GET  /strategy
  - POST /dispatch
- [x] LLM Status Renderer (renderer.py)
- [x] Supervisor UI (ui/) — **shadcn/ui**
- [ ] Core tests (dispatch + shared_memory — written, need to run)
- [ ] Action proposal timeout background scanner (running in API ✅)

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
export OPENAI_API_KEY=sk-...
# or
export ANTHROPIC_API_KEY=sk-ant-...
export LLM_PROVIDER=anthropic
```

## Running

```bash
# Backend
pip install -r requirements.txt
python -m swarmmind.db  # init DB (or just start API — it auto-inits)
python -m swarmmind.api.supervisor

# Frontend (new terminal)
cd ui && npm install && npm run dev
```

## Supervisor UI

- Polls `/pending` every 5 seconds
- Three tabs: Pending Proposals / Strategy Table / Status Renderer
- Approve/Reject buttons per proposal
- LLM Status Renderer: type a goal → get prose summary from shared context

## Context Broker Routing Rules (Phase 1)

| Keyword in goal | Routes to |
|----------------|-----------|
| "finance", "financial", "Q3", "quarterly", "revenue" | Finance Agent |
| "code", "review", "PR", "git", "python", "bug" | Code Review Agent |
| (no match) | Returns `no_route` status |

## Error Handling (Phase 1)

- **JSONDecodeError** → creates rejected proposal with error description
- **EmptyLLMResponse** → creates rejected proposal with error description
- **StrategyTableMiss** → creates rejected proposal, logs unknown situation
- **DB conflict (409)** → retries 3x with 100ms backoff, then raises `SharedMemoryConflict`

## Running Tests

```bash
pytest tests/ -v
```

## Related Docs

- `/Users/krli/workspace/SwarmMind/README.md` — public-facing README
- `/Users/krli/workspace/SwarmMind/README_zh.md` — Chinese README
- `/Users/krli/.gstack/projects/rx-opensource-team/krli-main-design-20260320-224059.md` — full design doc
