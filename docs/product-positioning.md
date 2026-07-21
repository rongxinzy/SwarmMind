# Product Positioning

> Document type: [A] target architecture document.
> Last repositioning: 2026-07 — 简化为普通 B/S 架构 Agent 聊天软件。

## One-line Positioning

SwarmMind 是一个开源的、普通 B/S 架构的 Agent 聊天软件：提供直连模型的普通对话、Agent 任务会话、项目工作区，以及基本的组织管理。

不承载任何理念叙事。它就是一个能用的聊天软件。

## 产品形态：Chat / Work 双模式

产品在 UI 上分为两个互相独立的顶层模式，侧边栏顶部用分段开关切换（参考 Kimi 的 Work | Chat 切换）：

- **Chat 模式**：直连模型的普通对话。只有对话列表和对话页。
- **Work 模式**：Agent 工作区。包含任务会话和 Project。

两个模式的会话列表、新建入口、历史完全分开，互不混排。组织管理是管理员的独立入口，不属于任一模式。

## 产品面

产品只有四个面，除此之外没有别的。

### 1. Chat（直连模型对话）

普通的模型对话，不经过任何 Agent runtime。

- 前端使用 Vercel AI SDK 直连模型。
- 用户能用什么模型，由后端分配决定（见"组织管理"）。
- 没有执行计划、没有 trace、没有 artifact 体系——就是聊天。

### 2. 任务（Agent 会话）

Agent 类型的会话，由 DeerFlow 作为执行内核。

- 用户提出任务，Agent 自主规划、调用工具、流式返回过程和结果。
- 支持 MCP 工具（可用范围由管理员授权决定）。

### 3. Project（项目工作区）

一个文件夹 workspace，可以开启多个会话。

- Project 内的会话性质都是 Agent 类型（任务会话）。
- 同一 Project 内的所有会话共享项目记忆。
- 没有 Promote 流程、没有审批、没有治理语义——就是一个带共享记忆的会话分组。

### 4. 组织管理

两层结构：组织 → 团队 → 成员。管理员负责：

- 开账户（创建用户、分配到团队）；
- 分配算力（配额）；
- 分配模型（决定用户/团队能用哪些模型）；
- 分配自定义 MCP 权限（决定用户/团队能用哪些 MCP server）。

角色只有两种：admin 和 member。

## Product Boundaries

SwarmMind 只做：

- 直连模型对话；
- Agent 任务会话（DeerFlow 执行）；
- 项目工作区（workspace + 多会话 + 项目内记忆共享）；
- 组织/团队/成员管理，配额、模型与 MCP 权限分配。

SwarmMind 不做：

- 任何理念叙事或平台故事；
- 审批流、治理中心、审计中心；
- Connector 平台 / 数据源同步；
- Agent 团队模板、工作流模板、模板市场；
- Runtime 池化、多租户隔离调度；
- 任务到项目的 Promote 流程；
- 把 trace / artifact 做成独立产品面。

## Who It Is For

需要一个自托管的、带基本组织和权限管理的 Agent 聊天软件的团队。
