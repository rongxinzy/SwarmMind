# SwarmMind API 偏差检视报告

> 日期：2026-04-26
> 基线版本：`8b0be61`
> 检视维度：当前 Swagger API 文档 vs. 产品设计意图（architecture.md + 用户故事 + UI 线框）

---

## 1. 当前 API 全景

后端共 **48 个端点**，分布在 4 个路由模块：

| 模块 | 端点数 | Tag |
|------|--------|-----|
| `supervisor.py` (直接 `@app`) | 35 | supervisor, system, runtime, projects, conversations, runs, agent-teams |
| `conversation_routes.py` | 10 | conversations |
| `llm_gateway_routes.py` | 3 | gateway |
| `llm_provider_routes.py` | 6 | llm-providers |

---

## 2. 偏差分类总览

| 优先级 | 类别 | 数量 | 说明 |
|--------|------|------|------|
| **P0 — 结构偏离** | 与架构基线冲突 | 4 | 必须修复，否则 Phase B/C 无法闭环 |
| **P1 — 功能缺口** | UI 线框需要但 API 缺失 | 5 | 阻塞前端实现对应页面 |
| **P2 — 语义不一致** | 存在但形态不符合产品语义 | 3 | 需要重构或扩展 |
| **P3 — 组织债务** | Tag/命名/聚合问题 | 2 | 可延后，但 Swagger 可读性差 |

---

## 3. P0 — 结构偏离（与 architecture.md 冲突）

### 3.1 Run 模型强制绑定 Conversation ❌

**问题：**
- `RunDB.conversation_id` 是 `NOT NULL`（`Field(foreign_key="conversations.id")`）
- `CreateRunRequest.conversation_id` 是必填字段

**架构期望：**
> `Run`: One execution attempt, **linked to a ChatSession or Project** — architecture.md §1

> Gateway resolves: work boundary: `ChatSession` or `Project`; namespace: `chat:{id}` or `project:{id}` — architecture.md §4.1

**影响：**
- 项目级原生 Run（不经过 ChatSession）无法创建
- 用户故事 §4.3 中 "Agent Team 接管正式项目启动" 产生的 Run 被迫挂靠到一个 conversation
- 虽然可以通过 `project.conversation_id` 间接关联，但这是绕路而非原生支持

**修复方向：**
- `RunDB.conversation_id` 改为 `nullable`
- `CreateRunRequest` 中 `conversation_id` 和 `project_id` 至少填一个（Pydantic `model_validator`）

---

### 3.2 Approval 模型是前 Project 遗产 ❌

**问题：**
- `ActionProposalDB` 字段：`agent_id`, `description`, `target_resource`, `confidence`, `status`
- **缺失：** `project_id`, `run_id`, `risk_tier`, `requested_capability`, `evidence`, `impact`, `approver_role`, `recovery_behavior`

**架构期望：**
> High-risk runs pause and create approval context with **`project_id`, `run_id`**, requested capability, evidence, impact, approver role, and recovery behavior. — architecture.md §7.2

**UI 线框期望：**
- 审批中心显示：项目名称、Team、触发阶段、风险等级、影响范围 — `40-approval-center.md` §1.3
- 审批详情显示：来源 run、来源 task、相关 artifact — `40-approval-center.md` §2.2

**当前 API 问题：**
- `GET /pending` 返回的 `ActionProposal` 没有项目上下文
- `POST /approve/{proposal_id}` 和 `POST /reject/{proposal_id}` 是动词端点，不是资源 RESTful 风格
- 没有审批详情端点（`GET /approvals/{id}`）
- 没有 "要求补充" 动作

**修复方向：**
- 新增 `ApprovalRequestDB`（或重构 `ActionProposalDB`），锚定 `project_id` + `run_id`
- 新增风险等级字段：`low | medium | high`
- 端点改为资源风格：`GET /approvals`, `GET /approvals/{id}`, `PATCH /approvals/{id}`

---

### 3.3 缺失独立的 AuditLog 存储 ❌

**问题：**
- 只有 `EventLogDB`（dispatch 日志），没有独立的 `AuditLogDB`
- 没有 `/projects/{id}/audit` 端点

**架构期望：**
> `EvidenceStore` owns: artifacts, **approvals, audit records**, provenance snapshots, evidence links — architecture.md §5

**用户故事期望：**
> 审批结果写入 `AuditLog` — `enterprise-crm-user-story.md` §4.8
> 驾驶舱看到审批与风险记录 — `enterprise-crm-user-story.md` §4.9

**修复方向：**
- 新增 `AuditLogDB`：审计事件类型、project_id、run_id、approval_id、actor、decision、reason、timestamp
- 新增 `GET /projects/{id}/audit` 和 `GET /projects/{id}/audit/stream`（如需实时）

---

### 3.4 缺失 Task/Kanban 数据模型与端点 ❌

**问题：**
- 无 `TaskDB` 模型
- 无 `/projects/{id}/tasks` 系列端点
- 无任务状态机（`todo | in_progress | blocked | done`）

**UI 线框期望：**
> 项目看板：To Do | In Progress | Blocked | Done — `30-projects-and-project-space.md` §5.3
> 点击任务查看负责人、来源 Workstream、关联 artifact — `30-projects-and-project-space.md` §5.4

**架构期望：**
> `TaskStore` owns: project task metadata, status, dependencies, human-readable assignment — architecture.md §5

**修复方向：**
- 新增 `TaskDB`：task_id, project_id, run_id, title, description, status, assignee_role, source_workstream, artifact_ids, priority, created_at, updated_at
- 新增端点：
  - `GET /projects/{id}/tasks`
  - `POST /projects/{id}/tasks`
  - `GET /projects/{id}/tasks/{task_id}`
  - `PATCH /projects/{id}/tasks/{task_id}`
  - `DELETE /projects/{id}/tasks/{task_id}`

---

## 4. P1 — 功能缺口（UI 需要但 API 缺失）

### 4.1 项目总览聚合数据缺失

**UI 线框：** `30-projects-and-project-space.md` §3.3

项目总览需要展示：
- 当前阶段（phase）
- 阻塞数量（blocked count）
- 待审批数量（pending approval count）
- 风险等级（risk level）
- 最近任务列表
- 最近产物列表
- 运行摘要
- 参与成员

**当前状态：**
- `Project` 模型只有：`title, goal, scope, constraints, status, next_step`
- 无 `phase`, `risk_level`, `blocked_count`, `pending_approval_count` 字段
- 前端需要调用 5+ 个端点才能组装总览

**建议：**
- 在 `ProjectDB` 增加 `phase`（当前阶段）和 `risk_level` 字段
- 考虑新增 `GET /projects/{id}/overview` 聚合端点，或让前端分别调用（推荐前者减少请求数）

---

### 4.2 审批中心 API 不完整

**当前端点：**
- `GET /pending` — 全局待审批列表（无项目筛选）
- `POST /approve/{proposal_id}` — 批准
- `POST /reject/{proposal_id}` — 拒绝

**UI 线框需要：** `40-approval-center.md`
- 按项目筛选审批
- 按风险等级筛选审批
- 审批详情（含来源 run、artifact、影响评估）
- "要求补充" 动作
- 审批跟踪（只读态）

**缺失端点：**
- `GET /approvals?project_id=xxx&risk_tier=high&status=pending`
- `GET /approvals/{approval_id}`
- `PATCH /approvals/{approval_id}`（支持 `approve`, `reject`, `request_supplement`）

---

### 4.3 项目时间线与风险页面无数据端点

**UI 线框：** `30-projects-and-project-space.md` §6

需要：里程碑、甘特、风险列表、阻塞链路。

**缺失：**
- 无 `Milestone` 模型
- 无 `Risk` 模型
- 无 `/projects/{id}/milestones` 或 `/projects/{id}/risks` 端点

---

### 4.4 产物库缺少来源追溯

**当前：** `GET /projects/{id}/artifacts` 返回 Artifact 列表

**UI 线框需要：** `30-projects-and-project-space.md` §7.3
- artifact 预览
- 来源任务
- 来源 Run
- 作者（agent role）
- 关联审批链路

**当前 `Artifact` 模型只有：** `artifact_id, conversation_id, project_id, message_id, name, artifact_type, created_at`

**缺失字段：** `run_id`, `task_id`, `author_role`, `content_url`（或 content blob）

---

### 4.5 项目设置缺少成员与 MCP Allowlist

**UI 线框：** `30-projects-and-project-space.md` §8.3

需要：
- 成员与权限管理
- MCP Allowlist

**当前状态：** 项目设置只有 `PATCH /projects/{id}` 修改基本信息

**缺失：**
- `/projects/{id}/members` 系列端点（已注明 deferred）
- `/projects/{id}/mcp-allowlist` 端点

---

## 5. P2 — 语义不一致

### 5.1 `EventLogDB` 不是 `AuditLog`

**当前：** `EventLogDB` 记录 goal dispatch 事件，字段是 `goal, situation_tag, dispatched_agent_id, outcome, latency_ms`

**期望：** Audit log 记录治理事件：审批决策、风险识别、策略变更、成员权限变更

**结论：** 这两个概念不能混用。需要新建 `AuditLogDB`。

---

### 5.2 `POST /approve/{id}` 和 `POST /reject/{id}` 不是 RESTful

**当前：** 两个动词端点分别处理批准和拒绝

**期望：** 审批是一个资源，状态变更用 `PATCH`

**建议：**
```
PATCH /approvals/{approval_id}
Body: { "decision": "approved" | "rejected" | "supplement_requested", "reason": "..." }
```

---

### 5.3 `supervisor` Tag 语义混杂

**当前 `supervisor` tag 包含：**
- `/pending` — 审批
- `/approve/{id}`, `/reject/{id}` — 审批操作
- `/status` — 系统状态
- `/strategy` — 路由策略
- `/dispatch` — 目标分发

**问题：** 审批、诊断、路由三个不同领域被塞进同一个 tag

**建议拆分：**
- `approvals` — 审批相关
- `routing` — `/dispatch`, `/strategy`
- `diagnostics` — `/status`

---

## 6. P3 — 组织债务

### 6.1 端点路径不一致

- `GET /models` 和 `GET /runtime/models` 返回相同内容（一个别名）
- `GET /conversations/{id}/artifacts` vs `GET /projects/{id}/artifacts` — 后者是正确的项目级产物入口，前者应标记为遗留

### 6.2 Gateway 端点的定位

`/gateway/v1/models` 和 `/gateway/v1/chat/completions` 是 OpenAI-compatible 代理端点，服务于外部 LLM 客户端调用，不是 SwarmMind UI 的产品 API。Swagger 中应明确区分或归入独立文档。

---

## 7. 验证清单：六条主流程覆盖度

对照 `02-page-map-and-flows.md` 六条主流程：

| 主流程 | 覆盖度 | 说明 |
|--------|--------|------|
| 1. 探索聊天 -> 正式项目 | ✅ 90% | ChatSession 完整，Promotion 存在，Project 创建存在。缺：提升时的语义压缩文档存储。 |
| 2. 项目启动 -> 持续推进 | ⚠️ 60% | Project CRUD 完整，Team 挂载存在，执行流存在。**缺：Task、Kanban、Milestone。** |
| 3. 审批暂停 -> 审批恢复 | ❌ 30% | `/pending`, `/approve`, `/reject` 存在但无项目上下文。**缺：风险等级、AuditLog、补充请求。** |
| 4. 技能治理 -> 项目生效 | ⚠️ 50% | LLM Provider 管理完整。**缺：MCP Allowlist、Skill 绑定到 Project/Team。** |
| 5. 项目完成 -> 资产沉淀 | ⚠️ 40% | Artifact 存在。**缺：WorkflowAssetStore、Team 资产沉淀端点。** |
| 6. 权限化工作台巡视 | ❌ 20% | **缺：Project Membership、RBAC、工作台聚合数据端点。** |

---

## 8. 结论与建议

### 8.1 是否偏离产品设计意图？

**是的，存在系统性偏离，但方向正确。**

当前后端已完成 Phase A（ChatSession 基础）和 Phase B 的大部分基础设施（Project 模型、Team 模板与实例、执行流入口）。但以下关键设计意图尚未在 API 中体现：

1. **Project 作为企业治理边界** — 审批、审计、任务都还没有真正锚定到 Project
2. **Run 独立于 Conversation** — Run 仍被 Conversation 强制绑定
3. **Governed execution** — 风险分级、审批上下文、审计链路都是缺失的

### 8.2 下一步建议

按优先级排序：

**Sprint 3 应完成（P0）：**
1. `RunDB.conversation_id` nullable + `CreateRunRequest` 校验
2. 重构 Approval 模型：`project_id`, `run_id`, `risk_tier` + RESTful 端点
3. 新增 `AuditLogDB` + `GET /projects/{id}/audit`
4. 新增 `TaskDB` + `/projects/{id}/tasks` CRUD

**Sprint 3 或 4（P1）：**
5. Project 增加 `phase`, `risk_level` 字段
6. Artifact 增加 `run_id`, `task_id`, `author_role` 字段
7. 新增 `GET /projects/{id}/overview` 聚合端点

**可延后（P2/P3）：**
8. Tag 重组
9. 里程碑与风险模型
10. Project Membership（等协作场景真实出现）

---

## 附录：完整端点清单与偏差标注

<details>
<summary>点击展开 48 个端点的逐条偏差标注</summary>

### System
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 1 | GET | `/health` | ✅ | — |
| 2 | GET | `/ready` | ✅ | — |

### Runtime
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 3 | GET | `/models` | ✅ | 与 `/runtime/models` 重复 |
| 4 | GET | `/runtime/models` | ✅ | — |

### Conversations
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 5 | GET | `/conversations` | ✅ | — |
| 6 | POST | `/conversations` | ✅ | — |
| 7 | GET | `/conversations/recent` | ✅ | — |
| 8 | GET | `/conversations/{id}` | ✅ | — |
| 9 | GET | `/conversations/{id}/messages` | ✅ | — |
| 10 | POST | `/conversations/{id}/messages` | ⚠️ | `include_in_schema=False`，前端用 stream |
| 11 | DELETE | `/conversations/{id}` | ✅ | — |
| 12 | GET | `/conversations/{id}/trace` | ✅ | — |
| 13 | POST | `/conversations/{id}/messages/stream` | ✅ | — |
| 14 | POST | `/conversations/{id}/clarification` | ✅ | — |
| 15 | POST | `/conversations/{id}/promote` | ✅ | — |
| 16 | GET | `/conversations/{id}/messages/{msg_id}/trace` | ✅ | — |
| 17 | GET | `/conversations/{id}/artifacts` | ⚠️ | 遗留端点，项目级产物应走 `/projects/{id}/artifacts` |
| 18 | POST | `/conversations/{id}/extract-artifacts` | ✅ | — |

### Projects
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 19 | GET | `/projects` | ✅ | — |
| 20 | GET | `/projects/{id}` | ⚠️ | 缺 phase/risk_level/blocked_count 等字段 |
| 21 | POST | `/projects` | ✅ | — |
| 22 | DELETE | `/projects/{id}` | ✅ | — |
| 23 | PATCH | `/projects/{id}` | ✅ | — |
| 24 | GET | `/projects/{id}/artifacts` | ✅ | — |
| 25 | POST | `/projects/{id}/messages/stream` | ✅ | 新增，正确 |
| 26 | GET | `/projects/{id}/runs` | ✅ | — |
| 27 | POST | `/projects/{id}/agent-team` | ✅ | — |
| 28 | GET | `/projects/{id}/agent-team` | ✅ | — |
| 29 | PATCH | `/projects/{id}/agent-team` | ✅ | — |
| 30 | DELETE | `/projects/{id}/agent-team` | ✅ | — |
| — | — | `/projects/{id}/tasks` | ❌ | **缺失** |
| — | — | `/projects/{id}/audit` | ❌ | **缺失** |
| — | — | `/projects/{id}/overview` | ❌ | **缺失** |

### Runs
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 31 | GET | `/runs/{id}` | ⚠️ | Run 强制需要 conversation_id |
| 32 | POST | `/runs` | ⚠️ | CreateRunRequest.conversation_id 必填，应可选 |
| 33 | PATCH | `/runs/{id}` | ✅ | 新增，正确 |
| 34 | GET | `/conversations/{id}/runs` | ✅ | — |

### Agent Teams
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 35 | GET | `/agent-teams` | ✅ | — |
| 36 | GET | `/agent-teams/{id}` | ✅ | — |
| 37 | POST | `/agent-teams` | ✅ | — |
| 38 | PATCH | `/agent-teams/{id}` | ✅ | — |
| 39 | DELETE | `/agent-teams/{id}` | ✅ | — |

### Approvals (Supervisor)
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 40 | GET | `/pending` | ❌ | 返回 ActionProposal，无 project_id/run_id/risk_tier |
| 41 | POST | `/approve/{id}` | ❌ | 动词端点，非 RESTful |
| 42 | POST | `/reject/{id}` | ❌ | 动词端点，非 RESTful |
| — | — | `/approvals` | ❌ | **缺失** |
| — | — | `/approvals/{id}` | ❌ | **缺失** |
| — | — | `/approvals/{id}` (PATCH) | ❌ | **缺失** |

### Routing / Diagnostics (Supervisor)
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 43 | GET | `/status` | ⚠️ | 放在 supervisor tag 下，应独立 |
| 44 | GET | `/strategy` | ⚠️ | 放在 supervisor tag 下，应独立 |
| 45 | POST | `/dispatch` | ⚠️ | 放在 supervisor tag 下，应独立 |

### LLM Gateway
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 46 | GET | `/gateway/v1/models` | ✅ | 运行时代理端点 |
| 47 | POST | `/gateway/v1/chat/completions` | ✅ | 运行时代理端点 |
| 48 | GET | `/gateway/status` | ✅ | 运行时代理端点 |

### LLM Providers
| # | Method | Path | 状态 | 偏差 |
|---|--------|------|------|------|
| 49 | GET | `/llm-providers` | ✅ | 非目标 but 功能完整 |
| 50 | POST | `/llm-providers` | ✅ | — |
| 51 | GET | `/llm-providers/{id}` | ✅ | — |
| 52 | PATCH | `/llm-providers/{id}` | ✅ | — |
| 53 | DELETE | `/llm-providers/{id}` | ✅ | — |
| 54 | GET | `/gateway/key` | ✅ | — |

</details>
