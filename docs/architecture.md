# SwarmMind 架构文档

> Document type: [A] target architecture baseline.
> 文档优先于代码；代码与本文档冲突时，重构代码。

## 0. 本版变更摘要

2026-07 定位重构：SwarmMind 从"AI workbench / 治理控制面"简化为**普通 B/S 架构的 Agent 聊天软件**，只保留四个产品面：

1. **Chat** — 直连模型对话（前端 Vercel AI SDK，不经过 Agent runtime）；
2. **任务** — Agent 会话（DeerFlow 执行）；
3. **Project** — workspace 文件夹 + 多 Agent 会话 + 项目内记忆共享；
4. **组织管理** — 组织 → 团队 → 成员，管理员分配账户、配额、模型、MCP 权限。

本版从架构中**移除**的概念（代码待裁剪清单见 `AGENTS.md`）：

- Promote to Project、审批流（ApprovalGate）、治理语义 AuditLog；
- AgentTeamTemplate、ProjectAgentTeamInstance、WorkflowTemplate、WorkflowAsset；
- ContextBroker 路由、策略表；
- LayeredMemory L1-L4、SharedMemory 全局 KV；
- Trace / Artifact 产品化表面（trace summary、artifact registry）；
- Connector 平台；
- Runtime Profile 池化、Runtime Container、多租户调度；
- LeadAgentProfile。

## 1. 术语表

### 1.1 产品层术语

| 术语 | 定义 |
|------|------|
| `Chat` | 直连模型的普通对话会话。不经过 DeerFlow runtime，无计划、无工具编排。 |
| `任务`（Task） | Agent 类型会话，由 DeerFlow runtime 执行，可调用工具与 MCP。代码中沿用 `ChatSession`（`session_type=task`）。 |
| `Project` | 一个文件夹 workspace + 一组任务会话 + 一份项目内共享记忆。 |
| `Organization` | 顶层组织实体。 |
| `Team` | 组织下的团队，成员归属于团队。 |
| `Member` | 用户。角色只有 `admin` / `member`。 |
| `ModelAllocation` | 模型与配额分配记录，可挂在组织 / 团队 / 成员三级，就近优先。 |
| `McpGrant` | MCP server 使用授权，由管理员定义白名单并授予团队或成员。 |

### 1.2 运行时术语

| 术语 | 定义 |
|------|------|
| `DeerFlow Runtime` | 任务会话的唯一执行内核。 |
| `LLM Gateway` | OpenAI 兼容的多 provider 模型路由，供 DeerFlow runtime 使用；同时是"可用模型清单"的数据来源。 |

### 1.3 禁止混用规则

- 产品层禁止裸用 `Agent` 一词。产品 UI 与文档只能说：**Chat / 任务 / Project / 团队**。
- `Chat` 与 `任务` 是两种会话类型，不得合并描述为"会话"。
- `Project` 不是"治理边界"，只是"会话分组 + 共享记忆 + 文件夹"。

## 2. 核心原则

### 2.1 B/S 单层产品

一个 Next.js 前端 + 一个 FastAPI 后端 + 一个 DeerFlow runtime。没有平台分层叙事，没有控制面/执行面之外的东西。

### 2.2 DeerFlow 只是任务会话的执行内核

任务会话由 DeerFlow 执行；Chat 会话完全不经过 DeerFlow。不引入第二个 runtime，也不把 DeerFlow 包装成别的概念。

### 2.3 Project 是唯一工作分组

Project = 文件夹 workspace + 会话集合 + 项目记忆。项目内所有会话共享项目记忆；项目之间记忆隔离。没有项目之上的更高层工作实体。

### 2.4 控制面只存必需数据

用户、组织/团队/成员、模型与配额分配、MCP 授权、会话、项目、项目记忆。除此之外不建存储实体。

### 2.5 权限从简

角色只有 admin / member。资源可见性 = 成员资格；资源可用性 = 管理员分配。不做细粒度 ACL、不做审批。

### 2.6 可配置、无硬编码

所有路径、密钥、连接串走环境变量或 `config.py`。

## 3. 目标架构

```
┌─────────────────────────────────────────────────────┐
│                   Next.js UI (Browser)               │
│                                                      │
│  Chat 面 ── Vercel AI SDK ──直连模型 provider──┐     │
│  任务 / Project / 管理面 ── REST + NDJSON ──┐   │     │
└─────────────────────────────────────────────│───│─────┘
                                              ▼   │
┌─────────────────────────────────────────────────┴─────┐
│              FastAPI 后端（控制面）                     │
│                                                      │
│  - 会话 API（Chat 元数据 / 任务会话编排）               │
│  - Project API（workspace、会话分组、项目记忆）         │
│  - 组织管理 API（组织/团队/成员、配额、模型、MCP 授权） │
│  - 模型清单与密钥下发（供 Chat 面 AI SDK 使用）         │
│  - LLM Gateway（多 provider 路由，供 runtime 使用）     │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│              DeerFlow Runtime（仅任务会话）            │
│  本地 runtime，启动时由后端生成 config                  │
└──────────────────────────────────────────────────────┘
```

要点：

- UI 分 **Chat / Work 双模式**，侧边栏顶部用分段开关切换（参考 Kimi 的 Work | Chat）。Chat 模式只有直连模型对话；Work 模式容纳任务会话与 Project；组织管理是 admin 的独立入口。两个模式的会话列表与新建入口完全分开。
- Chat 面不经过 FastAPI 的会话编排，也不经过 DeerFlow；后端只负责告诉前端"你能用哪些模型"以及对应的接入凭证。
- 任务会话由 FastAPI 编排（`conversation_execution`），调用 DeerFlow runtime，流式事件经 NDJSON 返回前端。
- 数据存储：SQLModel ORM + Alembic，`SWARMMIND_DATABASE_URL` 决定方言（本地默认 SQLite）。

## 4. 执行模型

### 4.1 Chat 路径

1. 前端从后端拉取当前用户可用的模型清单（来自 ModelAllocation）。
2. 用户选择模型，前端用 Vercel AI SDK 直连对应 provider 完成对话。
3. 后端只持久化会话与消息的元数据/内容，不产生执行 trace、计划或 artifact 产品面。

### 4.2 任务路径

1. 用户创建任务会话，后端编排 DeerFlow runtime 执行。
2. runtime 经 LLM Gateway 调用模型，按 MCPGrant 决定可用 MCP server。
3. 流式事件（思考、工具调用、结果）经 NDJSON 透传到前端。
4. 会话历史持久化，用于恢复与展示。不做 trace 重建、不做 artifact registry。

### 4.3 Project 路径

1. 创建 Project 时在后端配置的工作区根目录下建立文件夹。
2. Project 下可创建多个任务会话（仅任务类型，无 Chat）。
3. 项目记忆是一份 project 作用域的 KV 存储：项目内所有会话可读写，项目间隔离。
4. 删除 Project 时的文件处理策略（保留/删除）由配置决定。

## 5. 控制面数据边界

| Store | 内容 | 备注 |
|-------|------|------|
| `UserStore` | 用户、密码哈希、API token | 已实现（`repositories/user.py`） |
| `OrganizationStore` | 组织实体 | 待实现 |
| `TeamStore` | 团队，挂在组织下 | 待实现 |
| `TeamMembershipStore` | 成员-团队归属 + 角色 | 待实现（现有 project membership 是另一回事，待收敛） |
| `ModelAllocationStore` | 模型 + 配额分配（组织/团队/成员三级，就近优先） | 待实现；模型清单来自 LLM Gateway 配置 |
| `McpGrantStore` | MCP server 白名单与授权 | 待实现 |
| `ChatSessionStore` | 会话（`session_type`: chat / task），可挂在 project 下 | 已有 conversation/message 存储，待扩展类型字段 |
| `ProjectStore` | 项目：名称、workspace 路径、配置 | 已实现（`repositories/project.py`），待裁剪治理字段 |
| `ProjectMemoryStore` | project 作用域 KV，项目内会话共享 | 待实现（可复用 shared_memory 的 KV 机制，但作用域只有 project 一级） |

**明确删除的 Store**：AgentTeamTemplateStore、WorkflowAssetStore、ApprovalStore、独立治理语义的 TaskStore/RunStore、治理语义 AuditLog、LayeredMemory、ConnectorStore、RuntimeProfileStore（保留单一本地 runtime 的启动配置即可，不做 profile 池）。

## 6. 组织与权限模型

### 6.1 结构

```
Organization
└── Team (0..n)
    └── Member (0..n)，角色 admin / member
```

- admin：开账户、建团队、分配配额/模型/MCP 权限。
- member：使用被分配的资源。

### 6.2 分配规则

- **模型**：ModelAllocation 决定可用模型清单。查找顺序：成员 → 团队 → 组织，取最近一级；都无则不可用。
- **配额**：与 ModelAllocation 同级挂载，单位与计量方式在实现时定（token 数或调用次数，先取一种做简单）。
- **MCP 权限**：管理员维护 MCP server 白名单（名称、连接配置），按团队/成员授予；任务会话启动 runtime 时只注入已授权的 MCP server。

## 7. 非目标

以下是明确的非目标，不为它们保留扩展点：

- 审批流、治理中心、审计中心；
- Connector 平台、数据源同步、外部知识索引；
- Agent 团队模板、工作流模板、技能/插件市场；
- Runtime 池化、多租户 runtime 隔离调度、云原生部署编排；
- ChatSession → Project 的 Promote 流程；
- trace 重建、artifact registry 等执行证据产品面；
- 关键词/embedding 路由 broker；
- L1-L4 分层记忆体系；
- 细粒度文档级 ACL。

## 8. 实施路线

见 `docs/roadmap.md`。当前代码与新架构的偏差及待裁剪清单见 `AGENTS.md`。
