# Roadmap

> Document type: [A] target roadmap.
> 定位：普通 B/S 架构 Agent 聊天软件。四个产品面：Chat、任务、Project、组织管理。

## 原则

- 先裁剪，再建设：把旧定位遗留的表面下线，再补新定位缺的块。
- 每个里程碑都要有用户可直接使用的结果，不建"为未来准备"的脚手架。

## 里程碑

### M0. 收敛与裁剪

把与四个产品面无关的表面下线或删除。

- UI：移除/隐藏 trace、artifact registry、审批、connector 等页面与入口。
- API：下线 trace summary、artifact content、memory 查询、audit 等端点。
- 代码：删除 `AGENTS.md` 待裁剪清单中的模块及对应测试。
- 文档：`docs/ui/*` 线框按四个产品面重写。

### M1. Chat 直连

- UI 落地 Chat / Work 双模式：侧边栏顶部 Work | Chat 分段开关（参考 Kimi），两个模式的会话列表与新建入口完全分开。
- 后端提供"当前用户可用模型清单 + 接入凭证"端点（数据来自 ModelAllocation，模型来自 LLM Gateway 配置）。
- 前端用 Vercel AI SDK 实现 Chat 会话：选模型、多轮对话、历史持久化。
- 会话落库（`session_type=chat`），可列表、切换、删除。

### M2. 任务会话归位

现有 DeerFlow ChatSession 路径保留并归入 Work 模式的"任务"面。

- 会话类型区分 chat / task；现有 DeerFlow 会话标记为 task。
- 流式事件、标题生成、会话生命周期保持现有行为。
- 任务会话启动时按 McpGrant 注入已授权的 MCP server。

### M3. Project 工作区

- Project = workspace 文件夹：创建项目时建目录，路径根由配置决定。
- Project 下可建多个任务会话，项目页列出会话并可进入。
- 项目记忆：project 作用域 KV，项目内所有会话可读写，项目间隔离。
- 移除 Promote to Project 相关入口。

### M4. 组织管理

- 数据模型：Organization / Team / TeamMembership（角色 admin / member）。
- ModelAllocation：模型 + 配额，组织/团队/成员三级挂载，就近优先。
- McpGrant：MCP server 白名单维护与团队/成员授权。
- 管理后台 UI：开户、建团队、分配配额/模型/MCP 权限。
- 登录鉴权接通成员身份，各产品面按分配结果限制可用资源。

## 顺序

M0 → M1 / M2（可并行）→ M3 → M4。M4 的数据模型可以在 M1 之前先行（ModelAllocation 是 M1 模型清单的数据源）。

## 明确不在路线内

审批治理、connector 平台、模板市场、runtime 池化、Promote 流程、trace/artifact 产品面、分层记忆——见 `docs/architecture.md` §7 非目标。
