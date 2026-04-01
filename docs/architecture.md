# SwarmMind 架构文档

> 版本：v0.9.0
> 日期：2026-04-01
> 状态：DeerFlow-first 简化架构

## 1. 文档定位

这份文档是 SwarmMind 后续全面重构的唯一架构基线。

约束如下：

- 文档优先于现有代码实现。
- 如果文档与代码冲突，以文档为准，代码应被重构。
- 本文只描述目标架构，不为历史实现兼容性让步。

## 2. 核心原则

### 2.1 控制面与执行面分离

- `Broker`、`Router`、`Supervisor API/UI`、`Committer` 属于控制面。
- `DeerFlow Runtime`、`MCP tools`、`HTTP tools`、`Remote Service` 属于执行面。
- 控制面负责路由、策略、审批、提交、审计。
- 执行面负责动作执行，不直接提交共享控制面状态。

### 2.2 Project 是唯一工作边界

- `Project` 是一件事的唯一正式执行边界和长期工作空间。
- 任务、资料、档案、进度、问题、审批、约束、artifact、审计都归属于 `Project`。
- 多用户协作、workflow、审批、项目级可视化都必须发生在某个 `Project` 内。
- 系统允许用户在未创建 `Project` 时先开启轻量 `ChatSession`。
- `ChatSession` 可以在后续被提升为 `Project`。
- `Project` 同时是多用户共享、权限控制和审计归属的顶层边界。

补充原则：

- `ChatSession` 是一等入口，不是阉割模式或试用模式。
- 探索、提问、头脑风暴、快速验证默认优先走 `ChatSession`。
- 共享、治理、审批、长期推进默认优先走 `Project`。
- 可概括为：`Chat first for exploration, Project first for execution and governance.`

### 2.3 DeerFlow 是唯一执行内核

- SwarmMind 的核心执行统一采用 DeerFlow。
- 不把“同时抽象接入多个 Agent 框架”作为核心设计目标。
- 通用 Adapter 不是主架构中心，只能作为未来扩展点。

### 2.4 用户概念与运行时映射分离

- 对用户和界面层，SwarmMind 应保留 `Agent Team`、团队成员角色、团队协作、团队记忆等产品概念。
- 这些概念是产品语义，不等于必须存在一套独立的 Team runtime。
- 对内部实现，SwarmMind 默认不自建 Team runtime，而优先复用 DeerFlow 原生协作能力。
- 一个对用户可见的 `Agent Team`，在内部通常映射为 `AgentTeamTemplate + ProjectAgentTeamInstance + LeadAgentProfile + WorkflowTemplate + project-scoped DeerFlow memory`。
- 所有正式执行仍归属于 `Project`，而不是归属于某个独立 Team 实体。

### 2.5 DeerFlow 原生语义优先于抽象纯度

- DeerFlow 已有的稳定能力必须原样承接：`thread`、`chat/stream`、`artifact`、`upload`、`skill`、`plan_mode`、`subagent`。
- 不为了追求统一接口，削平 DeerFlow 的原生能力。
- 抽象层若与 DeerFlow 发生冲突，应优先修改抽象层。

### 2.6 Transport 与 Trust 分开建模

- `local / remote` 表示通信方式。
- `trusted / untrusted` 表示是否可纳入严格生命周期约束。
- DeerFlow 本体按 `local + trusted` 处理。
- DeerFlow 通过 MCP 或 HTTP 调用的外部系统，按各自的 `transport + trust` 级别处理。
- 企业内部系统接入的主路线采用 `MCP + Skill`。
- `MCP` 负责暴露企业系统工具及其输入输出。
- `Skill` 负责告诉 DeerFlow 何时、如何组合使用这些工具。
- SwarmMind 平台只补项目级启用、审批和审计，不复制下游系统的资源级权限模型。

### 2.7 数据边界必须分层

必须拆开九类控制面数据：

- `ProjectStore`：项目定义、范围、约束、绑定关系、运行边界。
- `ChatSessionStore`：轻量聊天会话、入口模式、提升关系和会话元数据。
- `AgentTeamTemplateStore`：可复用 Team 配置模板及其版本。
- `ProjectMemberStore`：项目成员、角色、权限和 actor 身份。
- `TaskStore`：任务状态、路由结果、handoff 元数据。
- `RunStore`：运行事实、状态迁移、事件索引和 usage 摘要。
- `ArtifactStore`：报告、代码 diff、文件输出、长日志、导出结果。
- `WorkflowAssetStore`：可复用的 playbook、knowledge pack、prompt pack 和工作流模板资产。
- `AuditLog`：审批结果、运行事件索引、关键决策轨迹。

DeerFlow memory 不属于上述控制面存储，它属于 DeerFlow 自身运行时记忆机制。

### 2.8 DeerFlow memory 不做强审计

- DeerFlow memory 是唯一长期运行记忆来源。
- DeerFlow memory 的异步总结、合并、覆盖由 DeerFlow 自身机制负责。
- SwarmMind 不强审计 DeerFlow memory 内部演化过程。
- SwarmMind 只审计 DeerFlow 运行请求、运行结果、artifact 索引和控制面元数据。
- 但 memory 命名空间必须被 `Project` 运行实例约束，不能跨项目共享。

### 2.9 Workflow Knowledge 是控制面资产，不是第二记忆系统

- Team / Workflow 内的文档、经验总结、SOP、复盘结论属于知识资产。
- 这些知识资产应以 `artifact`、`playbook`、`knowledge pack` 形式被版本化管理。
- 它们只能通过 `Project` 的上下文装配过程注入 DeerFlow。
- 它们不能与 DeerFlow memory 形成自动双写。

### 2.10 审批不是默认层，也不是事务系统

- 审批层默认关闭，不是 DeerFlow 主路径必需品。
- 审批若存在，只能拦截整轮高风险运行。
- 系统只能保证控制面元数据的提交一致性，不能保证外部副作用自动回滚。

能保证的：

- 未批准前，不提交控制面元数据。
- 运行失败时，不提交本轮控制面写入。

不能保证的：

- 已发出的 HTTP 请求自动回滚。
- 已写出的文件自动撤销。
- 第三方远端服务无副作用。

### 2.11 预执行探测允许存在，但不强制三段式

SwarmMind 不把 `prepare() -> propose() -> execute()` 作为 DeerFlow 主路径前提。

允许的预执行探测：

- 读文件、读代码、列目录。
- 读取只读数据库视图。
- 获取远端健康状态。

不允许的预执行探测：

- 写文件。
- 写数据库。
- 调用会修改外部状态的 API。

## 3. 目标架构

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

Optional control-plane capability:
  - ProfileManager
  - SkillCenter
```

组件职责：

- `Project`：定义一件事的范围、约束、资料边界和治理边界。
- `Router`：将目标归类为统一的 `task_kind`。
- `Strategy Table`：维护 `task_kind -> DeerFlowRuntimeProfile` 的映射。
- `Approval Policy`：可选地拦截高风险整轮运行。
- `DeerFlow Gateway`：把 SwarmMind 的目标、上下文、文件和运行策略映射到 DeerFlow 调用。
- `Committer`：统一提交任务状态、artifact 索引与审计记录。
- `AgentTeamTemplate`：用户在 Team 管理页配置和维护的团队模板。
- `ProjectAgentTeamInstance`：某个 Team 模板被加入 `Project` 后形成的项目内实例。
- `Workflow Template`：可选的产品层模板，用于组织 playbook、知识包和 prompt 约定。
- `SkillCenter`：管理 `MCP`、`Skill` 及其与运行 profile 的绑定关系。

`Agent Registry` 不属于主架构。如果未来确实引入第二执行引擎，再作为扩展能力恢复。

### 3.1 Project 作为顶层实体

`Project` 是 SwarmMind 的顶层工作空间实体。

最小结构如下：

```text
Project
  - project_id
  - name
  - objective
  - scope
  - constraints
  - status
  - member_refs
  - thread_bindings
  - artifact_roots
  - approval_policy_ref
  - team_instance_refs
```

`Project` 负责承载：

- 事情的资料与档案。
- 任务进度与问题列表。
- 审批策略与审计记录。
- 项目成员、权限和可见性边界。
- DeerFlow thread 绑定关系。
- 运行时上下文装配规则。
- 对工作流模板和外部能力的约束边界。

`Project` 不是任务列表容器，而是企业级共享工作空间：

- 同一个 `Project` 可以被多个用户共同查看和协作。
- 同一个 `Project` 下的资料、进度、artifact、run history 对有权限的成员可见。
- 审批、审计、运行约束都首先归属于 `Project`，而不是归属于某个工作流模板。
- 用户可以先在轻量 `ChatSession` 中探索需求，但一旦要共享、协作、审批或进入工作流推进，就应提升为 `Project`。

### 3.2 LeadAgentProfile 作为默认内部执行根

SwarmMind 默认以 DeerFlow `lead-agent` 作为单轮或多轮执行的根实体。

Lead agent 可以直接回答问题，也可以在 `plan_mode` 下调用 `subagents` 完成分解式任务。

最小结构如下：

```text
LeadAgentProfile
  - profile_name
  - deerflow_agent_name
  - model_name
  - thinking_enabled
  - plan_mode
  - subagent_enabled
  - default_thread_policy
  - prompt_pack_refs
  - skill_refs
```

约束：

- `LeadAgentProfile` 不是通用 Agent 抽象层，而是 DeerFlow 原生配置的控制面映射。
- `lead-agent` 是默认内部统一入口，因此不再单独设计 `TeamInterfaceAgent`。
- 是否启用 `subagents`，由 profile 和 task kind 决定，而不是先建一套自定义 Team runtime。
- 同一个 `LeadAgentProfile` 可以在产品层被包装成一个对用户可见的 `Agent Team` 入口。

### 3.3 AgentTeamTemplate 是产品层模板

`AgentTeamTemplate` 是用户在 Team 管理页看到和编辑的对象。它像 Python 的 `class`，描述一类可复用团队配置，而不是某个项目中的运行实体。

最小结构如下：

```text
AgentTeamTemplate
  - team_template_id
  - display_name
  - description
  - visible_role_names
  - default_profile_ref
  - workflow_template_refs
  - skill_refs
  - version
```

约束：

- Team 管理页展示的是模板，不是项目中的活跃实例。
- `AgentTeamTemplate` 不是独立执行根。
- 它不拥有独立 thread、独立审批边界或独立 runtime 生命周期。
- 用户看到的团队协作，在内部默认映射到 `LeadAgentProfile`、workflow assets 和 DeerFlow memory。
- 团队记忆在产品上可以存在，但内部默认等效为项目范围下的 workflow 资产与 DeerFlow 记忆组合。

### 3.4 ProjectAgentTeamInstance 是 Project 内实例

当某个 Team 模板被加入 `Project` 时，系统应创建一个 project-scoped 实例。它像 Python 的对象实例，继承模板默认配置，但绑定在具体项目边界内。

最小结构如下：

```text
ProjectAgentTeamInstance
  - project_team_instance_id
  - project_id
  - team_template_ref
  - template_version
  - selected_profile_ref
  - activated_workflow_refs
  - project_override_refs
  - status
```

约束：

- 它是控制面实例，不是独立 DeerFlow runtime。
- 它的职责是冻结模板版本、承载项目级 override，并为 Gateway 提供稳定映射。
- 同一个 `AgentTeamTemplate` 可以被多个 `Project` 实例化，但每个项目都必须得到独立 instance。
- run、audit、artifact 可以引用 `project_team_instance_id`，以表达“这个项目里的哪个团队在协作”。

### 3.5 WorkflowTemplate 仅作为可选控制面模板

如果产品上需要“Team / 工作流”概念，应只保留为控制面模板，不实现独立 runtime 实体。

它的作用是：

- 组织 prompt pack、playbook、knowledge pack。
- 为某类任务提供默认 `LeadAgentProfile`。
- 作为 Supervisor UI 中可复用的工作流入口。

最小结构如下：

```text
WorkflowTemplate
  - template_id
  - name
  - description
  - default_profile_ref
  - playbook_refs
  - knowledge_pack_refs
  - skill_refs
```

约束：

- `WorkflowTemplate` 不独立接活。
- 它不能拥有独立 thread、独立 memory 或独立审批边界。
- 它只能被 `Project` 引用，并在运行前由 Gateway 注入 DeerFlow 上下文。
- 它必须能映射成明确阶段、任务骨架和至少一种基础视图；当前最低要求是 `Kanban`。
- 它不应依赖隐藏式设计 Agent 才能成立；即使未来支持自然语言生成模板，模板最终也必须是显式可审阅资产。

### 3.6 ChatSession 与 Promote to Project

SwarmMind 允许用户在未创建 `Project` 时直接开始一个轻量聊天会话。

```text
ChatSession
  - chat_session_id
  - actor_id
  - status
  - entry_mode          (direct_model | default_agent)
  - thread_id
  - summary_ref
  - promoted_project_id
```

定位：

- `ChatSession` 是探索性、个人化、低治理成本的前项目入口。
- 它不是 workflow 协作边界，也不是多用户共享工作空间。
- 它可以由直连模型承接，也可以由默认 Agent 承接。
- 它应具备足够完整的可用性，像普通 AI 聊天产品一样直接可用。

约束：

- `ChatSession` 默认按单用户会话处理，不承载 workflow 模板。
- `ChatSession` 默认不挂项目级 `RBAC`、审批和协作看板。
- 一旦用户选择“提升为 Project”，系统必须创建正式 `Project`，并对聊天内容做语义压缩。
- 语义压缩结果应作为新 `Project` 的文档资产写入，而不是迁移整个 chat thread。
- 提升后，`Project` 成为后续执行和治理的正式边界；原 `ChatSession` 只保留为来源记录或只读入口。

## 4. DeerFlow 原生执行模型

### 4.1 运行时接口面

DeerFlow 原生是会话式 agent runtime，核心入口是 `chat()` / `stream()`，并围绕 `thread_id`、checkpointer、artifacts、uploads、skills 和 memory 组织能力。

SwarmMind 不再设计独立 `AgentInterface` 或多引擎对称抽象，只保留一层很薄的 DeerFlow 接入边界：

```python
class DeerFlowGatewayClient:
    def run_turn(
        self,
        message: str,
        *,
        thread_id: str,
        stream: bool = False,
        model_name: str | None = None,
        thinking_enabled: bool = True,
        plan_mode: bool = False,
        subagent_enabled: bool = False,
        agent_name: str | None = None,
    ) -> DeerFlowTurnResult: ...
```

`DeerFlowTurnResult` 至少保留：

- `final_text`
- `events`
- `artifacts`
- `usage`
- `thread_id`
- `uploaded_files`
- `runtime_flags`

配套管理接口尽量原样保留 DeerFlow 原生能力：

- `list_models()`
- `list_skills()`
- `get_memory()`
- `reload_memory()`
- `upload_files()`
- `list_uploads()`
- `get_artifact()`
- `reset_agent()`

### 4.2 DeerFlow Gateway 职责

SwarmMind 不改造 DeerFlow runtime 内部状态机，而是在其上增加一层很薄的 `DeerFlow Gateway`。

它负责：

- 在 `Project` 边界内装配运行上下文。
- 把用户目标整理成 DeerFlow 可执行的单轮 message。
- 选择 thread 策略：新 thread、复用 thread、持久 thread。
- 选择 runtime flags：`model_name`、`thinking_enabled`、`plan_mode`、`subagent_enabled`、`agent_name`。
- 选择要注入的 Project 资料、workflow playbook、knowledge pack 和 artifacts。
- 管理 uploads、stream events、final text、artifacts。
- 把 DeerFlow 结果映射成 SwarmMind 的 task、artifact、audit 记录。

它不负责：

- 改写 DeerFlow memory 机制。
- 发明 `AgentInterface`、`TeamRuntime` 一类中间层。
- 发明 DeerFlow 原生并不存在的 proposal 生命周期。
- 把 DeerFlow 强行包装成通用三段式任务引擎。

### 4.3 DeerFlowRuntimeProfile

路由层输出的不是角色名，而是 DeerFlow 运行配置。

最小 profile 结构如下：

```text
DeerFlowRuntimeProfile
  - profile_name
  - model_name
  - thinking_enabled
  - plan_mode
  - subagent_enabled
  - agent_name
  - thread_policy      (new | reuse | persistent)
  - stream_default     (true | false)
  - risk_level         (low | medium | high)
```

说明：

- 前五项直接映射 DeerFlow 原生运行参数。
- `thread_policy` 和 `stream_default` 属于 Gateway 调度策略，不侵入 DeerFlow 内核。
- `risk_level` 只为审批策略服务，不参与 DeerFlow 运行语义。

### 4.4 DeerFlow memory 边界

DeerFlow memory 是主运行闭环的一部分，SwarmMind 不在执行路径中接管它。

明确边界如下：

- DeerFlow memory 是唯一长期运行记忆来源。
- SwarmMind 不把同一轮运行结果再次写入自建长期记忆层。
- DeerFlow 执行后产生的 memory 更新，视为 DeerFlow 内部行为。
- SwarmMind 只读取 DeerFlow 暴露出的 memory 查询接口，不接管其内部总结流程。
- Project 和 WorkflowTemplate 的知识资产不自动同步进 DeerFlow memory。
- 所谓 “team memory” 在当前架构下等效于 `project-scoped` 的 DeerFlow agent memory，不再单独建模。
- DeerFlow memory 的可见范围必须受 runtime namespace 约束，而不是受模板名约束。

禁止出现双写：

- DeerFlow 在执行后异步更新 memory。
- SwarmMind 又把同一轮结果写入另一套长期记忆。
- Workflow playbook 或 knowledge pack 自动回写成 DeerFlow memory 条目。

否则会形成双重真相源，导致语义冲突和排障困难。

### 4.5 Runtime Namespace 与隔离规则

SwarmMind 必须把 DeerFlow 的会话式运行能力投影到显式命名空间中。

最小命名空间如下：

```text
RuntimeNamespace
  - project_id
  - profile_name
  - deerflow_agent_name
  - thread_namespace
  - memory_namespace
  - artifact_namespace
```

隔离规则：

- 同一个 workflow template 被多个 `Project` 使用时，必须得到不同的 namespace。
- `thread_id` 可以在同一 `project_id + profile_name` 内按策略复用，但不能跨项目复用。
- `memory_namespace` 至少要隔离到 `project_id + deerflow_agent_name`。
- `artifact_namespace` 至少要隔离到 `project_id`。
- Gateway 负责把 Project / Profile / Agent 标识稳定映射到 DeerFlow 的 thread 与 memory 标识。

## 5. 控制面数据边界

### 5.1 ProjectStore

`ProjectStore` 保存项目级边界和治理信息，例如：

- `project_id`
- `objective`
- `scope`
- `constraints`
- `status`
- `member_refs`
- `thread_bindings`
- `team_instance_refs`
- `approval_policy_ref`
- `issue_refs`
- `milestone_refs`

约束：

- Project 是任务、审批、artifact、audit 的上级边界。
- 正式协作记录必须归属于 `project_id`。
- 轻量 `ChatSession` 记录允许独立存在，但不等同于项目级治理记录。

### 5.2 ChatSessionStore

`ChatSessionStore` 保存用户在创建 `Project` 之前的轻量聊天会话元数据。

最小结构如下：

```text
ChatSession
  - chat_session_id
  - actor_id
  - entry_mode          (direct_model | default_agent)
  - title
  - title_status        (pending | generated | fallback | manual)
  - title_source        (llm | fallback | manual)
  - title_generated_at
  - thread_id
  - status
  - summary_ref
  - promoted_project_id
  - created_at
  - last_active_at
```

约束：

- `ChatSession` 默认是单用户私有入口，不是项目级共享空间。
- 它允许使用直连模型或默认 Agent，但不默认承载 workflow 模板、审批和多成员治理。
- 标题属于 `ChatSessionStore` 元数据，不属于 `RunStore`，也不应只存在于前端内存里。
- 标题生成应在首轮完整交换后触发，即至少有 1 条用户消息和 1 条 assistant 响应后再生成。
- 标题默认优先由 LLM 生成；若生成失败，则退化为基于首条用户消息的截断 fallback。
- 标题一旦生成，后续不应在每轮运行后反复改写；用户手动改名优先级最高。
- 若用户触发提升，`promoted_project_id` 必须建立与目标 `Project` 的映射。
- 提升时应生成语义压缩摘要，并作为目标 `Project` 的文档资产落库。
- 提升后不复用原 `ChatSession` thread；正式项目从新的项目上下文开始。

### 5.3 AgentTeamTemplateStore

`AgentTeamTemplateStore` 保存可复用的 Team 配置模板。

最小结构如下：

```text
AgentTeamTemplate
  - team_template_id
  - display_name
  - visible_role_names
  - default_profile_ref
  - workflow_template_refs
  - skill_refs
  - version
```

约束：

- Team 管理页只面向模板，不面向实例。
- 模板升级不应直接破坏已实例化到项目中的配置。
- `Project` 应引用 `ProjectAgentTeamInstance`，而不是直接复用全局模板可变状态。

### 5.4 ProjectMemberStore

`ProjectMemberStore` 采用正式 `RBAC`，保存项目成员、角色绑定和权限投影。

最小结构如下：

```text
Role
  - role_id
  - project_id
  - role_name
  - permission_keys

RoleBinding
  - project_id
  - actor_id
  - actor_type      (user | service)
  - role_id
  - bound_at
```

典型权限键：

- `project.view`
- `project.run`
- `project.approve`
- `artifact.read`
- `artifact.export`
- `workflow.use`
- `run.cancel`

约束：

- `Project` 默认是多成员可见的共享工作空间，而不是单用户私有线程。
- 所有查看、运行、审批、导出行为都必须可追溯到具体 `actor_id`。
- 权限控制先落在 `Project` 级 `RBAC`，再投影到 workflow、Run 和 Artifact 访问。
- 不允许仅靠前端隐藏实现权限隔离，控制面必须按权限键做服务端校验。

### 5.5 TaskStore

`TaskStore` 只保存可被控制面解释和回放的轻量元数据，例如：

- `project_id`
- `task_id`
- `goal`
- `task_kind`
- `selected_profile`
- `status`
- `run_id`
- `handoff_ref`
- `artifact_refs`

约束：

- 不保存长文正文。
- 不保存完整 DeerFlow memory 快照。
- 不保存大文件内容。

### 5.6 RunStore

`RunStore` 保存可回放的运行事实层，用于承接 `stream`、`partial`、tool 调用摘要和状态迁移。

最小结构如下：

```text
RunRecord
  - run_id
  - project_id
  - project_team_instance_id
  - task_id
  - actor_id
  - selected_profile
  - deerflow_agent_name
  - thread_id
  - status
  - started_at
  - finished_at
  - event_index_refs
  - usage_summary
  - artifact_refs
```

约束：

- `RunStore` 保存结构化事件索引和状态迁移，不保存全文日志 blob。
- 长日志、完整流式输出和大 payload 仍放入 artifact。
- `partial`、`cancelled` 和失败原因必须在 `RunStore` 中可查询。

### 5.7 ArtifactStore

`ArtifactStore` 是 DeerFlow 输出结果的主承载层。

保存内容包括：

- Project 资料、档案、导出结果。
- DeerFlow 生成的文件。
- 报告、分析结果、设计稿。
- 代码 patch、长日志、导出数据。
- 需要被下载、查看或回放的大 payload。

约束：

- 控制面只保存 artifact 索引，不复制大内容到 TaskStore 或 AuditLog。

### 5.8 WorkflowAssetStore

`WorkflowAssetStore` 保存可跨项目复用的工作流知识资产。

包括：

- workflow playbook
- SOP / checklist
- 经验总结
- 复盘文档
- prompt pack
- knowledge pack

约束：

- 工作流资产不与项目产物共用主语义。
- `Project` 只引用资产版本，而不拥有其源资产。
- 如需为项目冻结上下文，可在 `Project` 内保存引用快照或派生副本。

### 5.9 AuditLog

`AuditLog` 只保留关键决策和运行轨迹，不做全量事件归档仓库。

必须审计的内容：

- 运行属于哪个 `project_id`。
- 谁以哪个 `actor_id`、`actor_type` 发起了运行。
- Router 选中了哪个 `task_kind`。
- Strategy Table 选中了哪个 `DeerFlowRuntimeProfile`。
- 是否触发审批以及审批结果。
- 运行是否成功、部分成功或失败。
- 产生了哪些 artifact 引用。
- 使用了哪个 `project_team_instance_id`。
- 使用了哪个 `selected_profile` 和 `deerflow_agent_name`。

不纳入强审计的内容：

- DeerFlow memory 内部演化细节。
- DeerFlow memory.json 的逐字段变更历史。
- DeerFlow 异步 summarization 的中间过程。

### 5.10 Workflow Knowledge Assets

Workflow 知识资产属于控制面知识层，不属于 DeerFlow runtime memory。

使用方式：

- 作为 `WorkflowAssetStore` 中的版本化资产保存。
- 通过 `Project` 或 `WorkflowTemplate` 选择性启用。
- 由 Gateway 在运行前按需摘要、注入或以只读引用方式暴露给 DeerFlow。

演化方式：

- 允许新增、替换、版本升级。
- 允许通过复盘沉淀新的知识包。
- 不允许自动写成 DeerFlow memory。

### 5.11 ProfileManager

`ProfileManager` 是可选控制面能力，不属于 DeerFlow 运行主闭环。

它只负责用户偏好字段的管理与投影，例如：

- `style_preferences`
- `language_preferences`
- `tooling_preferences`
- `privacy_constraints`

约束：

- DeerFlow 不直接读写完整用户 profile 数据库。
- DeerFlow 只能接收经过投影和筛选后的少量偏好字段。
- `untrusted remote` 不得获得完整 profile 快照。

### 5.12 Deferred: LayeredMemory

`LayeredMemory` 不属于主架构承诺，不进入 DeerFlow 主执行路径。

它只保留为未来可选的控制面补充能力，前提是同时满足：

- DeerFlow 主路径已经稳定。
- 明确出现 DeerFlow memory 无法承载的结构化控制面需求。
- 新层不会与 DeerFlow memory 形成双写和双重真相源。

在满足以上条件前，不实现、不接线、不作为主方案依赖。

### 5.13 约束优先级

同一轮运行中，规则优先级固定为：

```text
Project constraints
  > Approval policy
  > Workflow template rules
  > Workflow playbook / knowledge pack
  > DeerFlow memory
```

原因是：

- `Project` 是这件事的最高边界。
- WorkflowTemplate 只服务于 Project。
- DeerFlow memory 是运行时记忆，不高于项目治理规则。

## 6. 生命周期与协作

### 6.1 轻量 ChatSession 路径

```text
user opens chat
  -> create or reuse ChatSession
  -> choose entry mode (direct model or default agent)
  -> DeerFlow run_turn in lightweight chat mode
  -> continue exploratory conversation
  -> optional semantic compression
  -> optional promote to Project
```

说明：

- 用户不必先创建 `Project` 才能开始对话。
- 轻量聊天适合需求探索、想法讨论和初步方案整理。
- `ChatSession` 默认不带 workflow 模板、审批和项目级可视化。
- 当用户需要共享、治理、协作或长期推进时，应提升为 `Project`。
- 提升动作的核心不是迁移原会话，而是把聊天语义压缩成项目初始文档资产。

### 6.2 DeerFlow 主路径

```text
goal or promoted chat
  -> resolve project boundary
  -> load promoted summary artifacts if any
  -> resolve actor identity and permissions
  -> resolve project team instance if any
  -> router selects task_kind
  -> strategy table selects DeerFlow runtime profile
  -> assemble project context + workflow assets
  -> optional run approval
  -> DeerFlow run_turn(stream or non-stream)
  -> collect events / artifacts / final text
  -> commit task transition / run record / artifact index / audit log
```

说明：

- DeerFlow 主路径不依赖 `prepare / propose / execute` 三段式。
- 正式协作运行必须先落入明确的 `Project` 边界。
- `Project` 可以从零创建，也可以由 `ChatSession` 提升而来。
- 若由 `ChatSession` 提升而来，正式项目应读取压缩后的文档资产，而不是继承整个 chat thread。
- 如果项目已挂载 `AgentTeamTemplate`，则正式执行前应先解析到对应的 `ProjectAgentTeamInstance`。
- 任何运行都必须绑定到明确的 `actor`、`project_id` 和 DeerFlow profile。
- 批准粒度只允许是整轮运行，不拆成伪造的子 proposal。
- 若审批复杂度高于其收益，应直接删除审批层，而不是继续扩张。

### 6.3 DeerFlow 协作路径

默认协作直接使用 DeerFlow 原生机制：

```text
goal
  -> project loads workflow assets if any
  -> select lead-agent profile
  -> DeerFlow plan_mode
  -> DeerFlow subagent decomposition
  -> artifacts / summaries / final answer
```

SwarmMind 只在以下场景补充工作流模板：

- 需要复用行业化 playbook。
- 需要为某类任务绑定默认 prompt pack / skill 组合。
- 需要在产品层展示“软件开发团队”“招聘团队”这类可选入口。

因此 WorkflowTemplate 是补充机制，不是默认协作主线。
正式协作入口默认由 DeerFlow `lead-agent` 承担，而不是自建 `TeamInterfaceAgent`。

如果多个成员围绕同一项目连续协作，统一入口应由 Gateway 结合 `thread_policy` 与 `lead-agent` 处理：

```text
member request
  -> Gateway intake
  -> normalize / classify / dedupe
  -> decide reuse-thread or new-thread
  -> dispatch to lead-agent
  -> collect artifacts / summaries / final answer
```

这种模式适用于：

- 多个成员会围绕同一工作流持续推进。
- 需要防止多人直接并发写入同一 thread。
- 需要先做上下文整理，再进入 DeerFlow 执行。

### 6.4 多用户并发语义

同一个 `Project` 允许多个成员同时工作，但并发必须显式建模。

规则如下：

- 并发的最小隔离单位是 `RunRecord`，不是整个 `Project`。
- 同一 `Project` 内允许多个 run 并行存在。
- `thread_policy=reuse` 只能在同一 `project_id + selected_profile` 边界内复用。
- 多用户场景下，是否复用 thread 应由 Gateway 策略决定，而不是由成员直接决定。
- 两个不同用户若同时发起运行，默认生成不同 `run_id`；是否共享 thread 由实例级策略判定。
- 审批、取消、重试都必须作用于明确的 `run_id`，不能对整个 `Project` 做隐式全局操作。

`thread_policy=reuse` 的最低约束：

- 只有被判定为同一工作流连续推进的请求，才允许进入同一 thread。
- 不同权限等级的 actor 不得复用同一个 thread。
- 同一时刻同一个 thread 只能有一个活跃写入 run。
- 若上下文主题发生明显切换，应强制创建新 thread。

详细判定规则后续应由单独 ADR 约束，但不再引入 `TeamInterfaceAgent` 作为主架构前提。

### 6.5 Remote 能力边界

远端能力属于 DeerFlow 通过 MCP 或 HTTP 使用的外部工具体系，不与 DeerFlow 并列为主执行引擎。

分级如下：

| 级别 | 说明 | 能力边界 |
| --- | --- | --- |
| `trusted` | 我们可控的进程或容器 | 可纳入完整生命周期约束 |
| `untrusted` | 第三方 HTTP 服务 | 只能按降级模式使用 |

`untrusted remote` 的降级模式：

- 可以提供建议和执行结果。
- 不能被当成严格无副作用的预执行探测参与者。
- 其结果只被视为 DeerFlow 的外部工具输出，是否沉淀由控制面决定。

### 6.6 失败语义

系统只承诺：

- DeerFlow 运行失败时，不提交本轮控制面元数据变更。
- 外部副作用由 DeerFlow 及其外部工具自行承担。
- `partial` 是一等状态，不伪装成成功。
- 已产生的 `RunStore` 事件索引允许保留，用于排障和审计。

状态集合固定为：

```text
pending | running | success | partial | failure | cancelled
```

## 7. 路由与审批

### 7.1 路由收敛

Broker 只输出一个主路由维度：`task_kind`。

路由规则：

- Project 先定义这件事的工作边界。
- `Router` 负责 `goal -> task_kind`。
- `Strategy Table` 负责 `task_kind -> DeerFlowRuntimeProfile`。
- `Role` 不是主路由对象。
- `Role` 如果存在，只是 DeerFlow 协作或控制面治理的附加语义。

示例：

```text
task_kind=code_review -> deerflow_profile=code-review
task_kind=deep_research -> deerflow_profile=research-plan-mode
task_kind=multi_step_delivery -> deerflow_profile=subagent-delivery
```

### 7.2 审批层原则

审批层完全重做后，只保留最小模型。

原则如下：

- 审批层默认关闭。
- 审批层不是系统必备组件。
- 审批对象只有整轮运行。
- 不为 DeerFlow 虚构 `ActionProposal`、`TeamPlan`、`ProfilePatch` 之类的中间对象。

最小审批对象：

```text
RunApproval
  - run_id
  - goal
  - selected_profile
  - risk_level
  - risk_reason
  - decision      (approved | rejected)
  - reviewer
  - decided_at
```

### 7.3 何时触发审批

只在以下情况触发审批：

- 命中 `high` 风险 profile。
- 将调用高风险外部能力。
- 用户明确要求人工确认后再执行。

除此之外，默认直通运行。

如果后续实践证明该模型依然复杂、收益不足或频繁阻塞主路径，则直接删除审批层。

## 8. 非目标

以下内容不进入主架构承诺：

- 云端技能社区。
- 自进化技能 DAG。
- 通用 MCP 工具市场。
- 自动补偿事务。
- 多执行引擎对称抽象。
- `AgentInterface` 抽象层。
- DeerFlow memory 的强审计与逐字段回放。
- 脱离 Project 独立运行的 Team runtime。
- Team / Workflow 自身拥有第二套长期运行记忆。

这些内容如需推进，应单独形成 ADR，不得污染主执行架构。

## 9. 实施路线

### 阶段 A

- 明确 DeerFlow 是唯一核心执行内核。
- 建立轻量 `ChatSession`，支持直连模型或默认 Agent 的会话入口。
- 建立 `Project` 作为顶层工作空间实体。
- 建立 `DeerFlow Gateway`，优先承接 `chat/stream/thread/artifact/upload/skill` 能力。
- 建立 `task_kind -> DeerFlowRuntimeProfile` 的策略表。
- 明确不引入 `AgentInterface`。

### 阶段 B

- 建立 `ProjectStore`，把任务、审批、artifact、audit 全部挂到 `project_id`。
- 建立 `ChatSessionStore` 和 `Promote to Project` 流程。
- 建立基于 `RBAC` 的 `ProjectMemberStore` 和 `RunStore`。
- 明确 thread、artifact、upload 是一等结果，不只返回文本。
- 正式以 DeerFlow memory 作为唯一长期记忆来源。
- 用 DeerFlow `plan_mode` / `subagent` 覆盖大部分多步骤任务。
- 明确 lead-agent 是默认统一入口。

### 阶段 C

- 建立 `AgentTeamTemplateStore` 与 `ProjectAgentTeamInstance`。
- 建立 `WorkflowTemplate` 与 `WorkflowAssetStore`。
- 建立 `TaskStore`、`RunStore`、`ArtifactStore`、`AuditLog`。
- 把 DeerFlow 结果稳定映射到 SwarmMind 的回放与审计视图。
- 仅在真实高风险场景下接入最小审批层。

### 阶段 D

- 将 Router 从关键词规则升级到 embedding 或 classifier。
- 在控制面增加 `ProfileManager` 与字段级投影策略。
- DeerFlow 路线稳定后，再评估是否需要补充更强的 workflow 模型，但不预设第二执行引擎。

## 10. 目标目录建议

```text
swarmmind/
├── chats/
├── projects/
├── members/
├── broker/
├── deerflow/
│   ├── gateway.py
│   ├── profiles.py
│   ├── artifacts.py
│   ├── uploads.py
│   └── policy.py
├── workflows/
│   ├── templates/
│   └── assets/
├── tasks/
├── runs/
├── artifacts/
├── audit/
└── api/
```

## 11. 结论

SwarmMind 的底座只需要先做对四件事：

1. 轻量 `ChatSession` 与正式 `Project` 的边界清晰。
2. DeerFlow 成为唯一执行内核。
3. `AgentTeamTemplate -> ProjectAgentTeamInstance` 的模板实例化模型清晰。
4. `lead-agent + subagents` 成为默认内部协作模型。
5. 成员、任务、运行、产物、工作流资产、审计等控制面边界清晰。

这五件事成立后，工作流模板、Team 管理、偏好管理和未来扩展能力才有稳定基础。

最终落地原则只有三条：

- 轻量探索可以发生在 `ChatSession`，正式协作与治理必须发生在 `Project` 内。
- DeerFlow 有稳定原生能力，就优先围绕它建设控制面。
- 任何新增层如果不能显著降低复杂度和风险，或会制造第二真相源，就不要进入主架构。
