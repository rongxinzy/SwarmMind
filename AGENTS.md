# SwarmMind — Agents Documentation

**AI agent team operating system. v0.9.0 — DeerFlow-first simplified architecture.**

## Project Overview

SwarmMind is an **operating system for AI agent teams** — built with control-execution separation, Project as the primary workspace, and DeerFlow as the exclusive execution kernel.

### Core Principles

- **Control-Execution Separation**: Supervisor API/UI, Broker, Router control the execution flow
- **DeerFlow-First**: DeerFlow is the exclusive execution kernel, no alternative execution engines
- **Project-Centric**: Project is the only formal workspace boundary for tasks, approvals, artifacts, and audits
- **Team Templates**: AgentTeamTemplate (reusable) + ProjectAgentTeamInstance (project-scoped)
- **Lightweight Chat**: ChatSession for exploration, can be promoted to formal Project

### Current Status

- **Version**: v0.9.0 (DeerFlow-first simplified architecture)
- **Repo**: https://github.com/rongxinzy/SwarmMind
- **Phase**: Phase A (ChatSession + Project + DeerFlow Gateway foundation)
- **Frontend**: shadcn/ui (React 18 + Tailwind CSS + Vite)
- **Backend**: Python (FastAPI)
- **Storage**: SQLite (Phase 1)
- **Python env**: uv

## Python Environment

```bash
uv sync          # install deps
uv run python -m swarmmind.api.supervisor   # run API
```

**Secrets** → `.env` (gitignored). Copy `.env.example` to `.env` and fill in keys.

## Target Architecture

```text
Human Supervisor
        |
        v
Supervisor API / UI
       / \
      v   v
Pre-Project Chat
  |- ChatSession
  |- ChatSessionStore
      |
      | promote
      v
Project Workspace
  |- Project Control Plane
  |    |- Broker
  |    |- Router
  |    |- Strategy Table
  |    |- Approval Policy (optional)
  |    |- DeerFlow Gateway
  |    |- Committer
  |
  |- DeerFlow Runtime Kernel
  |    |- lead-agent
  |    |- subagents
  |    |- thread / checkpointer
  |    |- chat / stream
  |    |- uploads / artifacts
  |    |- skills / MCP tools
  |    |- plan_mode
  |    |- memory middleware
  |
  |- Control-plane stores
  |    |- ProjectStore
  |    |- ChatSessionStore
  |    |- AgentTeamTemplateStore
  |    |- ProjectMemberStore
  |    |- RuntimeProfileStore
  |    |- TaskStore
  |    |- RunStore
  |    |- ArtifactStore
  |    |- WorkflowAssetStore
  |    |- AuditLog
  |
  |- Team and workflow layer
       |- Agent Team templates
       |- Project team instances
       |- Workflow templates
       |- Prompt / playbook refs
       |- Runtime profile refs
```

### Key Components

- **Project**: Top-level workspace with scope, constraints, members, and audit boundary
- **ChatSession**: Lightweight entry for exploration, can be promoted to Project
- **AgentTeamTemplate**: Reusable team configuration template (like a class)
- **ProjectAgentTeamInstance**: Project-scoped team instance (like an object)
- **DeerFlow Gateway**: Maps SwarmMind goals to DeerFlow execution
- **DeerFlow Runtime**: Exclusive execution kernel (lead-agent + subagents)
- **Strategy Table**: Maps task kinds to DeerFlow runtime profiles
- **Approval Policy**: Optional risk-based approval layer
- **AuditLog**: Records key decisions and run trajectories

## Implementation Structure

```
swarmmind/
├── AGENTS.md              ← Agents documentation
├── CLAUDE.md              ← Developer documentation (softlinked to AGENTS.md)
├── README.md
├── README_zh.md
├── pyproject.toml         ← uv project definition
├── .env.example          ← secrets template (not committed)
├── .env                  ← actual secrets (gitignored, symlinked from worktree)
├── requirements.txt       ← pip fallback
├── .gitignore
├── swarmmind/
│   ├── __init__.py
│   ├── config.py           ✅ load_dotenv + LLM configuration
│   ├── llm.py              ✅ unified LLMClient (single entry point for all LLM calls)
│   ├── db.py               ✅ SQLite schema + health check + seeding
│   ├── models.py           ✅ Pydantic models (all database tables)
│   ├── context_broker.py   ✅ dispatch() + keyword routing + strategy table
│   ├── shared_memory.py    ✅ KV store + last-write-wins + 409 retry
│   ├── renderer.py         ✅ LLM Status Renderer (uses LLMClient)
│   ├── agents/
│   │   ├── base.py         ✅ BaseAgent (uses LLMClient)
│   │   ├── finance.py      ✅ FinanceAgent
│   │   ├── code_review.py  ✅ CodeReviewAgent
│   │   └── general_agent.py ✅ GeneralAgent (DeerFlow-driven, handles uncategorized tasks)
│   └── api/
│       └── supervisor.py   ✅ FastAPI supervisor REST API
├── ui/                    ✅ Supervisor web UI
│   ├── src/App.tsx         ✅ Full supervisor UI
│   ├── vite.config.ts
│   └── tailwind.config.js
└── tests/
    ├── test_dispatch.py     ✅ routing, strategy table, unknown goals
    └── test_shared_memory.py ✅ KV store tests
```

### Data Layer Separation

SwarmMind separates 10 types of control-plane data:

- **ProjectStore**: Project definitions, scope, constraints, member bindings
- **ChatSessionStore**: Lightweight chat sessions, metadata, promotion records
- **AgentTeamTemplateStore**: Reusable team configuration templates
- **ProjectMemberStore**: Project member roles, permissions, RBAC
- **RuntimeProfileStore**: DeerFlow runtime configuration profiles
- **TaskStore**: Lightweight task metadata, routing results
- **RunStore**: Execution records, state transitions, event indexes
- **ArtifactStore**: Project files, reports, outputs, exports
- **WorkflowAssetStore**: Reusable playbooks, knowledge packs, prompt packs
- **AuditLog**: Approval decisions, run events, key decision trails

**Note**: DeerFlow memory is separate and managed by DeerFlow itself.

## Phase A Implementation (Current)

**DeerFlow-first simplified architecture - Phase A foundation**

- [x] **SQLite schema + health check** (db.py)
  - Auto-healing database with table creation
  - Migration support for schema updates
- [x] **Models** (models.py)
  - Pydantic models for all database tables
- [x] **SharedMemory** (shared_memory.py)
  - KV store with 409 retry and last-write-wins conflict resolution
- [x] **ContextBroker** (context_broker.py)
  - dispatch() + keyword routing + strategy table
- [x] **Agent Adapters** (agents/)
  - BaseAgent: Abstract base with memory utilities
  - FinanceAgent: Specialized for financial analysis
  - CodeReviewAgent: Specialized for code review tasks
  - GeneralAgent: DeerFlow-powered fallback with SwarmMind identity
- [x] **DeerFlow Integration** (agents/general_agent.py)
  - DeerFlowClient integration
  - Thread management and artifact handling
  - Streaming support with structured events
- [x] **Supervisor API** (api/supervisor.py)
  - GET  /pending (paginated)
  - POST /approve/{id}
  - POST /reject/{id}
  - GET  /status?goal=...
  - GET  /strategy
  - POST /dispatch
  - POST /chat (stateless LLM query via render_status)
- [x] **LLM Status Renderer** (renderer.py)
  - LLM-based status generation from shared context
- [x] **Supervisor UI** (ui/) — **shadcn/ui**
  - Three-tab interface: Pending Proposals / Strategy Table / Status Renderer
- [x] **Core tests** (dispatch + shared_memory)
  - Comprehensive test coverage
- [x] **Action proposal timeout scanner** (5 min background thread)
  - Automatic cleanup of stale proposals

## Phase B (Planned)

- [ ] ProjectStore implementation
- [ ] ChatSessionStore + "Promote to Project" workflow
- [ ] RuntimeProfileStore + RuntimeProvisioner
- [ ] ProjectMemberStore with RBAC
- [ ] RunStore with structured event indexing
- [ ] ArtifactStore for file management
- [ ] AuditLog for compliance tracking
- [ ] DeerFlow memory boundary enforcement

## Phase C (Future)

- [ ] AgentTeamTemplateStore + ProjectAgentTeamInstance
- [ ] WorkflowTemplate + WorkflowAssetStore
- [ ] TaskStore with metadata tracking
- [ ] Containerized Runtime instances
- [ ] Embedding-based routing (keyword → embedding)

## Phase D (Long-term)

- [ ] ProfileManager with field-level projection
- ] Multi-tenant runtime pools
- [ ] Enhanced workflow models
- [ ] No second execution engines

## Core Design Principles

### 1. Control-Execution Separation
- **Control Plane**: Broker, Router, Supervisor API/UI, Committer
- **Execution Plane**: DeerFlow Runtime, MCP tools, HTTP tools, Remote Services
- Control plane handles routing, strategy, approval, commit, and audit
- Execution plane handles task execution, doesn't directly submit control state

### 2. Project as the Primary Boundary
- **Project** is the only formal workspace boundary
- Tasks, approvals, artifacts, and audits all belong to a Project
- Multi-user collaboration, workflows, approvals happen within Projects
- ChatSession can be promoted to Project with semantic compression

### 3. DeerFlow-First Execution
- DeerFlow is the exclusive execution kernel
- No alternative execution engines or LLMClient fallbacks
- All formal execution goes through DeerFlow Runtime
- Runtime unavailable returns explicit error, not graceful degradation

### 4. Agent Team Architecture
- **AgentTeamTemplate**: Reusable configuration templates (control plane)
- **ProjectAgentTeamInstance**: Project-scoped instances (not independent runtimes)
- No separate Team runtime - uses DeerFlow's native collaboration

### 5. Memory and Data Boundaries
- **DeerFlow memory**: Only long-term memory source, managed by DeerFlow
- **Control-plane data**: Separated into 10 distinct stores (see Implementation Structure)
- **No double-write**: Avoid dual truth sources between systems

### 6. Runtime Namespace Isolation
- Runtime namespace: project_id + profile_name + deerflow_agent_name
- Thread, memory, and artifact namespaces must be properly isolated
- Gateway maps Project/Profile/Agent to DeerFlow identifiers

### 7. Approval as Optional Layer
- Approval layer is optional, not part of main execution path
- Only approves entire risky runs, not sub-proposals
- If complexity > benefit, remove approval layer entirely

## Coding Rules

- **❌ 禁止硬编码个人路径** — 任何路径必须通过环境变量或配置传递，禁止在代码中写死 `/home/xxx`、`/Users/xxx` 等个人目录路径
- **✅ 路径必须可配置** — 使用 `os.environ.get("PATH_ENV_VAR", None)` 或 `config.py` 中的配置项
- **✅ 可选依赖** — 非核心功能必须作为 optional dependency，优雅降级

## LLM Configuration

> **Worktree 注意**：`worktree/`.env 通过符号链接指向主仓库的 `.env`，确保两边共享同一份密钥。

**`.env`** (gitignored — never commit):
```bash
LLM_PROVIDER=openai                              # 或 anthropic
LLM_MODEL=qwen3.5-plus
ANTHROPIC_API_KEY=sk-sp-...                     # Alibaba DashScope Coding Plan
ANTHROPIC_BASE_URL=https://coding.dashscope.aliyuncs.com/v1  # OpenAI 兼容协议
```

**`.env.example`** (safe to commit — placeholder values):
```bash
LLM_PROVIDER=openai
LLM_MODEL=qwen3.5-plus
ANTHROPIC_API_KEY=your-api-key-here
ANTHROPIC_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
```

## Running

**所有开发/构建命令必须通过 `make` 执行。** PM2 + Makefile：
```bash
make install       # install all deps (uv sync + pnpm install)
make dev           # start both backend + frontend via PM2
make build         # build frontend for production
make typecheck     # TypeScript type check (frontend only)
make test          # run Python backend tests
make logs          # tail PM2 logs
make stop          # stop all services
make status        # show PM2 status
```

**⚠️ PM2 Process Management Rules:**
- **Use `pm2 stop`** to stop processes gracefully — this prevents auto-restart
- **DO NOT use `kill -9`** on PM2-managed processes — PM2 detects death and auto-restarts, creating a zombie loop
- Only use `kill -9` as a last resort if `pm2 stop` hangs
- `make restart` keeps the backend on `pm2 restart`, but recreates the frontend process so the UI always picks up the current repo `cwd`

**Individual services (local dev):**
```bash
make restart-api   # restart backend only (pick up code changes)
make restart-ui    # recreate frontend only (fixes stale PM2 cwd)
make restart       # restart both
make backend       # start backend only (first time)
make frontend      # start frontend only (first time)
```

## Supervisor UI

- Polls `/pending` every 5 seconds
- Three tabs: Pending Proposals / Strategy Table / Status Renderer
- Approve/Reject buttons per proposal
- LLM Status Renderer: type a goal → get prose summary from shared context

## Current Routing Strategy (Phase A)

| Keyword in goal | Routes to | Runtime Profile |
|----------------|-----------|----------------|
| "finance", "financial", "Q3", "quarterly", "revenue" | GeneralAgent | Default profile |
| "code", "review", "PR", "git", "python", "bug" | GeneralAgent | Default profile |
| (no match) | **GeneralAgent** | Default profile |

### Future Routing Strategy (Phase B+)

| Task kind | Routes to | Runtime Profile |
|-----------|-----------|----------------|
| code_review | DeerFlow runtime profile | code-review specific |
| deep_research | DeerFlow runtime profile | research-plan-mode |
| multi_step_delivery | DeerFlow runtime profile | subagent-delivery |
| finance_analysis | DeerFlow runtime profile | finance-expert |

**Strategy Table**: Maps `task_kind -> DeerFlowRuntimeProfile`
- Dynamic profile selection based on task requirements
- Profile includes model, thinking_mode, plan_mode, subagent_enabled
- No hard-coded model names in routing logic

## Error Handling (Phase 1)

- **JSONDecodeError** → creates rejected proposal with error description
- **EmptyLLMResponse** → creates rejected proposal with error description
- **StrategyTableMiss** → creates rejected proposal, logs unknown situation
- **DB conflict (409)** → retries 3x with 100ms backoff, then raises `SharedMemoryConflict`

## Running Tests

```bash
make test          # uv run pytest tests/ -v
```

## Related Docs

- `/Users/krli/workspace/SwarmMind/README.md` — public-facing README
- `/Users/krli/workspace/SwarmMind/README_zh.md` — Chinese README
- `/Users/krli/.gstack/projects/rx-opensource-team/krli-main-design-20260320-224059.md` — full design doc

## Database Management

SwarmMind uses a **custom SQLite management system** rather than ORM migrations:

### Initialization & Health Check
- `init_db()` creates all tables and indexes from `SCHEMA` and `INDEXES` constants
- `health_check()` auto-creates missing tables (self-healing mechanism)
- Called on API startup to ensure database is ready

### Migrations
- Manual SQL-based migrations (no Alembic or ORM migrations)
- Current migration: `_migrate_conversation_title_columns()` adds new columns to existing tables
- Schema changes require manual SQL编写
- No version control for migrations - careful with production changes

### Seeding
- `seed_default_agents()` inserts default agent records and routing strategies
- Called after database initialization
- Default "general" agent now has SwarmMind identity (updated from DeerFlow)

## Agent System Architecture

### Current Implementation (Phase A)
- **BaseAgent**: Abstract base with memory utilities and database loading
- **GeneralAgent**: DeerFlow-powered fallback with SwarmMind identity
- **FinanceAgent**: Specialized for financial analysis (keyword-based routing)
- **CodeReviewAgent**: Specialized for code review (keyword-based routing)

### Agent Registration
- Agents stored in `agents` table (agent_id, domain, system_prompt)
- System prompts loaded from database at runtime via `_load_system_prompt()`
- Default "general" agent updated to identify as SwarmMind, not DeerFlow

### Memory Architecture
- **LayeredMemory**: 4-layer memory system (L1_TMP, L2_TEAM, L3_PROJECT, L4_USER_SOUL)
- **SharedMemory**: KV store with last-write-wins conflict resolution and 409 retry
- **DeerFlow Memory**: Separate long-term memory managed by DeerFlow runtime
- **Memory Boundaries**: Enforced at project + agent level isolation

### Runtime Integration
- **DeerFlow Gateway**: Thin layer mapping SwarmMind goals to DeerFlow execution
- **Thread Management**: Policy-based (new/reuse/persistent) via Gateway
- **Artifact Handling**: Projects bound artifact namespaces
- **Stream Support**: Real-time event streaming for UI updates