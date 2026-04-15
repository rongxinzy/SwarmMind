# SwarmMind — Agents Documentation

**AI agent team operating system. v0.9.0 — DeerFlow-first simplified architecture.**

> **Architecture baseline**: `docs/architecture.md` is the single source of truth.
> If code conflicts with architecture, code must be refactored.

---

## Documentation Taxonomy

SwarmMind 文档按性质分为两类，阅读和使用时请区分：

### A. 前瞻性架构文档 (Target Architecture)

**定义**: 描述目标状态、设计决策、长期演进方向的文档。它们是代码的“应然”状态。

| 文档 | 定位 | 更新频率 | 与代码的关系 |
|------|------|----------|-------------|
| `docs/architecture.md` | 主架构基线 | 低频，重大架构决策时更新 | 文档优先于代码；冲突时重构代码 |
| `DESIGN.md` | 设计系统规范 | 低频，设计系统演进时更新 | 实现必须遵循的规范之源 |
| `docs/ui/*.md` | UI线框与交互规则 | 中频，新页面/流程时更新 | 实现参考，但受DESIGN.md约束 |
| `docs/enterprise-crm-user-story.md` | 场景验证文档 | 低频，架构验证时更新 | 用于验证架构闭环，不反向覆盖架构 |

**特征**:
- 描述 "应该是什么" (what should be)
- 包含 Phase B/C/D 的前瞻性设计
- 术语表、核心原则、非目标声明
- 实施路线图 (Phase A-D)

### B. 工程状态文档 (Implementation Status)

**定义**: 描述当前代码已实现的工程状态、接口定义、部署配置的文档。它们是代码的"实然"状态。

| 文档 | 定位 | 更新频率 | 来源 |
|------|------|----------|------|
| `AGENTS.md` (本节) | 当前工程状态总览 | 高频，每次迭代更新 | 代码实现 + 架构映射 |
| `docs/README.md` | 文档治理规则 | 中频 | 文档体系元数据 |
| `docs/archive/chat-ui-gap-analysis.md` | UI差距分析（已归档） | 一次性调研 | 对比 DeerFlow 与 SwarmMind 现状 |
| `docs/archive/ui-migration-plan.md` | UI移植执行计划（已归档） | 一次性执行文档 | 具体移植步骤 |

**特征**:
- 描述 "当前实现了什么" (what is implemented)
- Phase A 已实现项用 ✅ 标记
- 文件级别的实现状态 (如 `config.py ✅`)
- 运行命令、环境配置、测试指令

### 使用指南

**开发者应首先阅读**: 取决于你的目标

- **要做架构设计或技术决策** → 先读 A 类文档 (architecture.md, DESIGN.md)
- **要理解当前代码能做什么** → 先读 B 类文档 (AGENTS.md 实现状态)
- **要实现新功能** → 对照 A 类确定目标，对照 B 类确定起点

**禁止事项**:
- 不要用已实现的代码反向修改 A 类文档的定义（应通过架构决策流程更新）
- 不要在 B 类文档中描述尚未实现的 Phase B/C/D 特性（应链接到 A 类文档的相关章节）

---

## Architecture References

核心架构已完整写入以下文档，AGENTS.md 仅保留实现状态映射：

> 📋 **图例**: [A] = 前瞻性架构文档 | [B] = 工程状态文档

| Topic | Document | 类型 |
|-------|----------|------|
| 术语表（禁止裸用 `Agent`） | `docs/architecture.md` §1 | [A] |
| 核心原则（11 条） | `docs/architecture.md` §2 | [A] |
| 目标架构图 | `docs/architecture.md` §3 | [A] |
| DeerFlow 执行模型（Gateway、Namespace、Profile/Instance） | `docs/architecture.md` §4 | [A] |
| 控制面数据边界（10 Store） | `docs/architecture.md` §5 | [A] |
| 生命周期与协作（ChatSession / 主路径 / 并发 / 失败） | `docs/architecture.md` §6 | [A] |
| 路由与审批 | `docs/architecture.md` §7 | [A] |
| 非目标 | `docs/architecture.md` §8 | [A] |
| 实施路线（Phase A-D） | `docs/architecture.md` §9 | [A] |
| 目标目录结构 | `docs/architecture.md` §10 | [A] |
| UI 设计系统（颜色、字体、动效） | `DESIGN.md` | [A] |
| UI 线框与交互规则 | `docs/ui/` | [A] |
| 场景验证 | `docs/enterprise-crm-user-story.md` | [A] |
| 当前工程状态（本节下方） | `AGENTS.md` §Current Status | [B] |
| 实现结构映射 | `AGENTS.md` §Implementation Structure | [B] |
| 运行与部署配置 | `AGENTS.md` §Running | [B] |
| 文档治理规则 | `docs/README.md` | [B] |

## Current Status

- **Version**: v0.9.0 (DeerFlow-first simplified architecture)
- **Repo**: https://github.com/rongxinzy/SwarmMind
- **Phase**: Phase A (ChatSession + Project + DeerFlow Gateway foundation)
- **Frontend**: shadcn/ui (React 18 + Tailwind CSS + Vite)
- **Backend**: Python (FastAPI)
- **Storage**: SQLModel ORM + Alembic, dialect-aware via `SWARMMIND_DATABASE_URL` (SQLite default for local/dev)
- **Python env**: uv

## Workspace Layout

本地开发工作区结构（仅供参考，不作为版本控制的一部分）：

```
SwarmMindProject/              ← 本地工作区根目录（无git管理）
├── SwarmMind/                 ← 主项目（所有开发、测试、提交都在这里）
│   ├── swarmmind/             # Python后端代码
│   ├── ui/                    # React前端代码
│   ├── docs/                  # 架构文档、UI线框
│   ├── DESIGN.md              # 设计系统规范
│   ├── AGENTS.md              # 本文件：工程状态
│   ├── pyproject.toml         # 依赖定义
│   └── .git/                  # ✅ 唯一git仓库
│
└── deer-flow/                 ← 上游依赖源码副本（仅用于学习参考）
    └── backend/               # 本地源码，无物理依赖关系
```

### 说明

- **SwarmMind** 是唯一的版本控制仓库，所有代码提交指向 `https://github.com/rongxinzy/SwarmMind`
- **deer-flow** 是上游依赖的本地副本，仅用于调研和学习，不直接参与构建
- SwarmMind 通过 `pyproject.toml` 的 Git 依赖引用 deerflow-harness，而非本地路径

### 为什么不维护父项目git

1. SwarmMind 和 deer-flow 已经各自独立管理版本
2. 父项目没有实质代码，提交只是子模块引用更新
3. 增加维护复杂度（每次子模块更新需同步提交父项目）
4. 版本配套关系可通过 SwarmMind 的依赖声明体现

## Implementation Structure

```
swarmmind/                         ← Python package root
├── __init__.py
├── config.py                      ✅ load_dotenv + LLM configuration
├── db.py                          ✅ dialect-aware engine + Alembic-backed schema init + session scope
├── db_models.py                   ✅ SQLModel ORM table definitions
├── models.py                      ✅ Pydantic models (API/service layer)
├── context_broker.py              ✅ dispatch() + keyword routing + strategy table
├── shared_memory.py               ✅ KV store + last-write-wins + 409 retry
├── layered_memory.py              ✅ 4-layer memory (L1_TMP, L2_TEAM, L3_PROJECT, L4_USER_SOUL)
├── renderer.py                    ✅ LLM Status Renderer
├── agents/
│   ├── base.py                    ✅ BaseAgent (abstract base with memory utilities)
│   └── general_agent.py           ✅ DeerFlowRuntimeAdapter (runtime orchestration shell, compat alias: GeneralAgent)
├── repositories/                  ✅ Repository layer (SQLModel + CRUD per domain)
│   ├── agent.py
│   ├── action_proposal.py
│   ├── strategy.py
│   ├── event_log.py
│   ├── memory.py
│   ├── conversation.py
│   ├── message.py
│   └── runtime_catalog.py
├── services/
│   ├── conversation_execution.py  ✅ ChatSession send/stream orchestration
│   ├── conversation_support.py    ✅ Message/title persistence helpers
│   ├── conversation_trace_service.py ✅ conversation_id -> thread_id trace orchestration
│   ├── lifecycle.py               ✅ startup lifecycle + cleanup scanner
│   ├── runtime_bridge.py          ✅ sync/async bridge helpers for DeerFlow runtime calls
│   ├── runtime_event_processing.py ✅ stream capture + event normalization helpers
│   ├── runtime_support.py         ✅ runtime binding/model/runtime-option helpers
│   ├── stream_events.py           ✅ DeerFlow event -> UI stream event translation
│   ├── trace_checkpoint_storage.py ✅ raw checkpoint storage access
│   ├── trace_provider.py          ✅ parsed checkpoint provider boundary
│   └── trace_service.py           ✅ collaboration trace reconstruction
├── runtime/
│   ├── bootstrap.py               ✅ DeerFlow Runtime bootstrap + config generation
│   ├── profile.py                 ✅ RuntimeProfile management
│   ├── models.py                  ✅ Runtime data models
│   ├── catalog.py                 ✅ Model catalog for runtime profiles
│   └── errors.py                  ✅ Runtime error types
└── api/
    ├── supervisor.py              ✅ FastAPI app assembly + supervisor/system endpoints
    └── conversation_routes.py     ✅ conversation route registration and compatibility exports

ui/                                ← Supervisor web UI (Vite + React + shadcn/ui)
├── src/
│   ├── App.tsx                    ✅ Full supervisor UI shell
│   ├── components/workspace/      ✅ Split chat workspace components
│   └── core/chat/                 ✅ Chat stream/scroll/types helpers
├── vite.config.ts
└── tailwind.config.js

tests/
├── conftest.py                    ✅ Shared test fixtures
├── test_dispatch.py               ✅ Routing, strategy table, unknown goals
├── test_shared_memory.py          ✅ KV store tests
├── test_layered_memory.py         ✅ Layered memory tests
├── test_conversation_titles.py    ✅ ChatSession title generation
├── test_conversation_stream.py    ✅ Streaming conversation tests
├── test_conversation_trace_service.py ✅ Conversation trace orchestration tests
├── test_runtime_bridge.py         ✅ Sync/async bridge tests
├── test_general_agent_stream_bridge.py ✅ GeneralAgent sync/async bridge regression tests
├── test_general_agent_stream_events.py ✅ GeneralAgent stream event processing tests
└── test_runtime_model_catalog.py  ✅ Runtime model catalog tests
```

## Phase Roadmap

> 📋 **图例**: ✅ = 已实现并交付 | 🚧 = 进行中 | ⏳ = 规划中（见 architecture.md Phase B/C/D）

### Phase A (Current — Implementation Status [B])

本阶段描述的是**当前代码已实现**的工程状态。如需了解 Phase B/C/D 的设计目标，参见 `docs/architecture.md` §9。

- [x] ORM schema + health check + seeding
- [x] SQLModel + Alembic + Repository layer migrated from raw sqlite3
- [x] Pydantic models for all database tables
- [x] SharedMemory (KV store + conflict resolution)
- [x] ContextBroker (dispatch + keyword routing + strategy table)
- [x] Agent Adapters (BaseAgent, DeerFlowRuntimeAdapter)
- [x] DeerFlow Runtime bootstrap + config generation
- [x] Runtime profile + model catalog
- [x] Supervisor API (REST endpoints)
- [x] LLM Status Renderer
- [x] Supervisor UI (shadcn/ui, three-tab interface)
- [x] Core tests (dispatch, shared_memory, layered_memory, runtime catalog, conversation)

---

### Phase B/C/D (Forward-Looking — Target Architecture [A])

> ⚠️ **以下阶段描述的是目标架构设计，尚未实现**。如需了解当前实现状态，参见上方 Phase A。
> 完整的前瞻性设计参见 `docs/architecture.md` §9。

### Phase B

- [ ] ProjectStore — tasks, approvals, artifacts, audit all on `project_id`
- [ ] ChatSessionStore + Promote to Project (semantic compression)
- [ ] RuntimeProfileStore + RuntimeProvisioner
- [ ] ProjectMemberStore with RBAC
- [ ] RunStore with structured event indexing
- [ ] ArtifactStore for file management
- [ ] AuditLog for compliance tracking
- [ ] DeerFlow memory boundary enforcement
- [ ] DeerFlow `plan_mode` / `subagent` for multi-step tasks
- [ ] Lead-agent as default unified entry

### Phase C

- [ ] AgentTeamTemplateStore + ProjectAgentTeamInstance
- [ ] WorkflowTemplate + WorkflowAssetStore
- [ ] TaskStore with metadata tracking
- [ ] Runtime pool by `runtime_profile_id`
- [ ] Minimal approval layer (only for real high-risk scenarios)

### Phase D

- [ ] Router upgrade: keyword → embedding/classifier
- [ ] ProfileManager with field-level projection
- [ ] Runtime Container: `tenant + runtime_profile_id` isolation pools
- [ ] Evaluate enhanced workflow models (no second execution engine)

> 📋 以上 Phase B/C/D 的完整设计规范、约束条件和非目标声明，参见 `docs/architecture.md` §9。

---

## Python Environment

```bash
uv sync          # install deps
uv run python -m swarmmind.api.supervisor   # run API
```

Secrets → `.env` (gitignored). Copy `.env.example` to `.env` and fill in keys.

Database config in `.env`:

```bash
# Preferred: full SQLAlchemy URL, so switching SQLite / PostgreSQL / MySQL only needs config changes
SWARMMIND_DATABASE_URL=sqlite:///swarmmind.db

# Schema init strategy
# - migrate: Alembic upgrade to head (default, recommended)
# - create_all: SQLModel metadata bootstrap (tests / isolated dev only)
SWARMMIND_DB_INIT_MODE=migrate

# Legacy SQLite-only fallback; only used when SWARMMIND_DATABASE_URL is unset
# SWARMMIND_DB_PATH=swarmmind.db
```

## Running

All dev/build commands via `make`:

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

PM2 rules: use `pm2 stop` (not `kill -9`). `make restart` recreates frontend for correct cwd.

```bash
make restart-api   # restart backend only
make restart-ui    # recreate frontend only
make restart       # restart both
make backend       # start backend only (first time)
make frontend      # start frontend only (first time)
```

## Coding Rules

- **No hardcoded personal paths** — all paths via env vars or `config.py`
- **Paths must be configurable** — use `os.environ.get()` or config entries
- **Optional dependencies** — non-core features must gracefully degrade
- **Python**: 4-space indent, type hints where practical, snake_case, Ruff (double quotes, 240-char line)
- **TypeScript**: PascalCase components, camelCase helpers, grouped imports, shadcn-style primitives

## LLM Configuration

`.env` (gitignored):
```bash
SWARMMIND_DATABASE_URL=sqlite:///swarmmind.db
SWARMMIND_DB_INIT_MODE=migrate
LLM_PROVIDER=openai
LLM_MODEL=qwen3.5-plus
ANTHROPIC_API_KEY=sk-sp-...
ANTHROPIC_BASE_URL=https://coding.dashscope.aliyuncs.com/v1
```

## Error Handling

- **JSONDecodeError** → rejected proposal with error description
- **EmptyLLMResponse** → rejected proposal with error description
- **StrategyTableMiss** → rejected proposal, logs unknown situation
- **DB conflict (409)** → retries 3x with 100ms backoff, then `SharedMemoryConflict`

## Running Tests

```bash
make test          # uv run pytest tests/ -v
```
