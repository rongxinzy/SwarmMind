# Agent Action Roadmap

> Document type: [B] agent execution guide.
> Audience: coding/design/product agents evolving SwarmMind from the current codebase.
> Rule: this document translates the target docs into action. It does not redefine product direction or architecture.

## 1. Mission

Every agent should advance the four product surfaces defined in `docs/product-positioning.md`:

**Chat（直连模型对话）、任务（DeerFlow 执行的 Agent 会话）、Project（workspace 文件夹 + 多任务会话 + 项目内记忆共享）、组织管理（组织 → 团队 → 成员，分配账户/配额/模型/MCP 权限）。**

判断标准：一个任务是否让这四个面更简单可用。是，就做；不是，就不做。

There is no broader narrative to serve. SwarmMind is a usable chat application, not a platform story.

## 2. Source Order

When documents disagree, use this order:

1. `docs/product-positioning.md` for product boundaries and the four surfaces.
2. `docs/architecture.md` for terminology, execution paths, control-plane store boundaries, and non-goals.
3. `docs/roadmap.md` for milestone order (M0-M4) and immediate priorities.
4. `DESIGN.md` for visual system, density, components, and UI style.
5. `docs/ui/*` for page structure, flows, and interaction details.
6. `AGENTS.md` for current implementation status and runnable commands.
7. `docs/sprint-*` for dated execution snapshots only.

Do not use sprint plans or current code to silently rewrite the target architecture. If the target is wrong, change the target docs explicitly first.

## 3. First Five Questions

Before coding, answer these in scratch notes or PR summary:

1. Which milestone does this work belong to: M0, M1, M2, M3, or M4 (see `docs/roadmap.md`)?
2. Which product surface does it improve: Chat, 任务, Project, or 组织管理?
3. What is the user-visible result that proves the slice is real?
4. Does it introduce anything from the non-goals list in `docs/architecture.md` §7? (If yes, stop.)
5. Which legacy-positioning module does it remove, stop depending on, or explicitly leave untouched (see the 待裁剪清单 in `AGENTS.md`)?

If any answer is vague, narrow the slice before implementing.

## 4. Operating Loop

Use this loop for every meaningful product change:

1. **Orient**
   Read `AGENTS.md`, then the relevant target docs. Confirm current implementation with `rg`, tests, and local code inspection.

2. **Choose a Vertical Slice**
   Prefer one user-visible path over broad scaffolding. A slice should include backend state, API behavior, frontend surface, and tests when applicable.

3. **Preserve the Boundary**
   DeerFlow is only the execution kernel for 任务 (task) sessions. Chat does not go through it. Do not introduce approvals, connectors, templates, routing brokers, or anything else on the non-goals list in `docs/architecture.md` §7.

4. **Hide the Machinery**
   Product UI should say Chat, 任务, Project, 团队, model, and history. Do not lead with agent graphs, runtime checkpoints, orchestration, thread IDs, or control-plane internals.

5. **Implement in Existing Shapes**
   Follow existing repository, service, route, React component, and shadcn/Tailwind patterns. Do not introduce a new framework or parallel runtime.

6. **Verify**
   Add or update focused tests. For UI work, verify light/dark behavior, text fit, interaction states, centered composer behavior, and neutral/black action styling per `DESIGN.md`.

7. **Update Status**
   If implementation status changes, update `AGENTS.md` or the relevant [B] plan. If product target changes, update the [A] docs explicitly.

## 5. Immediate Roadmap

Tracks below mirror the milestones in `docs/roadmap.md`. Order: M0 first, then M1/M2 in parallel, then M3, then M4.

### Track 0: M0 — 收敛与裁剪 (Convergence and Removal)

Goal: take every surface that does not belong to the four product faces offline, and converge the remaining UI on `DESIGN.md` v5.

Work order:

1. Remove or hide trace, artifact registry, approval, connector, and audit pages and entries from the UI.
2. Take the trace summary, artifact content, layered-memory query, and audit endpoints offline.
3. Delete the modules in the `AGENTS.md` 待裁剪清单, together with their tests.
4. Rewrite `docs/ui/*` wireframes around the four product surfaces.
5. Converge the remaining UI on `DESIGN.md` v5: replace blue primary actions and focus glow with neutral/black action styling; simple centered cardless login; composer-first empty chat; quiet icon-rail navigation.

Primary files:

- `AGENTS.md` 待裁剪清单中的模块与对应 tests
- `DESIGN.md`
- `ui/src/index.css`
- `ui/src/App.tsx`
- `ui/src/components/auth/LoginPage.tsx`
- `ui/src/components/chat/*`
- `ui/src/components/layout/Sidebar.tsx`

Acceptance:

- The four product surfaces are the only navigation entries left.
- Main action styling is black/neutral, not blue.
- Empty chat has a centered headline and composer.
- No trace/artifact/approval/connector UI or API responds to traffic.

### Track 1: M1 — Chat 直连 (Direct-Model Chat)

Goal: a plain model conversation that does not touch any agent runtime.

Work order:

1. Backend endpoint: current user's available model list + access credentials (from ModelAllocation; models come from LLM Gateway configuration).
2. Frontend Chat surface built on the Vercel AI SDK: pick a model, multi-turn conversation, persisted history.
3. Sessions persist with `session_type=chat`; list, switch, and delete work.

Primary files:

- `swarmmind/api/` (new Chat surface endpoints)
- `swarmmind/db_models.py` (session type field)
- `ui/src/components/chat/*`

Acceptance:

- A user can hold a multi-turn direct-model conversation and resume it after refresh.
- The Chat path never invokes DeerFlow or the conversation orchestration used by task sessions.

### Track 2: M2 — 任务会话归位 (Task Sessions)

Goal: keep the existing DeerFlow session path dependable and label it as the 任务 surface.

Work order:

1. Distinguish `session_type` chat / task; mark existing DeerFlow sessions as task.
2. Preserve stable create, switch, delete, recover, send, and stream behavior, plus title generation.
3. Inject only McpGrant-authorized MCP servers when a task session starts its runtime.

Primary files:

- `swarmmind/services/conversation_execution.py`
- `swarmmind/services/conversation_support.py`
- `swarmmind/services/stream_events.py`
- `swarmmind/api/conversation_routes.py`
- `ui/src/components/chat/*`

Acceptance:

- A user can resume a recent task session after refresh.
- A failed run leaves enough state to retry or explain failure.
- The UI never requires users to understand DeerFlow thread/checkpoint details.

### Track 3: M3 — Project 工作区 (Project Workspace)

Goal: Project = workspace folder + task session grouping + shared project memory. Nothing more.

Work order:

1. Create a workspace folder when a Project is created; the workspace root comes from configuration.
2. Multiple task sessions under one Project; the project page lists sessions and links into them.
3. Project memory: project-scoped KV, readable/writable by all sessions in the project, isolated between projects.
4. Remove Promote-to-Project entries and any governance fields from the Project surface.

Primary files:

- `swarmmind/db_models.py`
- `swarmmind/repositories/project.py`
- `swarmmind/api/` project routes
- `ui/src/components/project/*`

Acceptance:

- Creating a Project creates a real folder and a working session list.
- Two sessions in the same Project share project memory; sessions in different Projects do not.

### Track 4: M4 — 组织管理 (Organization Management)

Goal: organization → team → member, with admin-managed accounts, quotas, models, and MCP permissions.

Work order:

1. Data model: Organization / Team / TeamMembership with roles admin / member.
2. ModelAllocation: model + quota, attachable at organization / team / member level, nearest level wins.
3. McpGrant: MCP server whitelist maintenance and grants to teams or members.
4. Admin UI: create accounts, create teams, assign quotas / models / MCP permissions.
5. Wire login identity into every product surface so each surface only exposes allocated resources.

Acceptance:

- An admin can onboard a member end to end: account, team, model allocation, MCP grant.
- A member sees only the models and MCP servers they were allocated.

## 6. Explicit Deferrals

Agents should not spend effort on anything in the `docs/architecture.md` §7 non-goals list, including:

- approval flows, governance centers, audit centers;
- connector platforms and data-source sync;
- agent team templates, workflow templates, skill/plugin marketplaces;
- runtime pooling and multi-tenant runtime scheduling;
- ChatSession → Project promote flows;
- trace reconstruction and artifact registries as product surfaces;
- keyword/embedding routing brokers;
- L1-L4 layered memory;
- fine-grained document-level ACLs;
- a second workflow or agent runtime.

These are non-goals, not backlog items. Do not keep extension points for them.

## 7. Slice Template

Use this shape when proposing or implementing a new slice:

```text
Slice:
Milestone (M0-M4):
Product surface (Chat / 任务 / Project / 组织管理):
User-visible outcome:
Legacy modules removed or left untouched:
Runtime boundary:
Files likely touched:
Tests / verification:
Docs to update:
Non-goal check (architecture.md §7):
```

Example:

```text
Slice: Chat 直连 model list endpoint + AI SDK conversation
Milestone (M0-M4): M1
Product surface: Chat
User-visible outcome: user picks an allocated model and holds a persisted multi-turn conversation
Legacy modules removed or left untouched: none removed; conversation orchestration untouched (task-only)
Runtime boundary: no DeerFlow involvement; backend only serves model list + credentials and persists messages
Files likely touched: db_models.py, api/ chat routes, ui/src/components/chat/*
Tests / verification: API tests for model list, UI smoke test for conversation flow
Docs to update: AGENTS.md
Non-goal check: no trace, no artifact registry, no runtime orchestration on the Chat path
```

## 8. Review Checklist

Before calling a change complete:

- It makes one of the four product surfaces simpler or more usable.
- Chat stays off the DeerFlow path; DeerFlow stays the only task-session runtime.
- It introduces nothing from the `docs/architecture.md` §7 non-goals list.
- It uses product terms (Chat / 任务 / Project / 团队) instead of raw runtime terms.
- It is visible in the UI or API, not just scaffolded.
- It has focused tests or an explicit verification reason.
- It follows `DESIGN.md` v5.
- It updates implementation-status docs when the status changed.

Good work here is not more surface area. Good work is four surfaces that are simple and usable.
