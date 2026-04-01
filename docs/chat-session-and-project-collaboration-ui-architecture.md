# ChatSession 与 Project 协作台前端架构

> 日期：2026-04-01
> 目的：吸收 deer-flow 前端会话实现的有效机制，并将其翻译为 SwarmMind 的前端会话与协作架构
> 关联文档：`docs/architecture.md`、`docs/ui/10-workbench-and-chat.md`、`docs/ui/30-projects-and-project-space.md`、`docs/deer-flow-research.md`

## 1. 文档定位

这不是 deer-flow 前端源码解读，也不是纯 UI 线框文档。

本文回答的是一个更具体的问题：

- SwarmMind 的前端会话层应该如何承接 DeerFlow 的 `thread` 能力
- 如何同时保持 SwarmMind 自己的产品语义：`ChatSession`、`Project`、`Agent Team`
- 哪些 deer-flow 机制应被复用，哪些不应被产品层直接照搬

## 2. 核心结论

### 2.1 deer-flow 值得吸收的不是页面，而是 thread-first 运行模型

deer-flow 前端把一次会话的关键状态统一挂在 `thread_id` 上：

- 消息流
- 标题
- artifact
- 上传文件
- todo
- subtask
- 导出 / 删除 / 重命名

这一点是正确的。

SwarmMind 应保留同样的内部运行原则：

- 单次运行上下文必须有稳定主键
- 所有流式状态、产物和运行细节应围绕该主键聚合
- 不应把消息、artifact、run detail、上传状态拆成多套互不关联的前端状态

### 2.2 但 SwarmMind 不能直接做成 thread-first 产品

SwarmMind 的用户概念不能退化成 deer-flow 的内部术语。

对用户：

- 入口一：`ChatSession`
- 正式执行边界：`Project`
- 产品协作概念：`Agent Team`

对内部：

- `ChatSession` 通常映射到一个 deer-flow `thread`
- `Project 协作台` 通常映射到一个 project-scoped deer-flow `thread` 或 thread 集
- `Agent Team` 不作为前端主路由主键，而作为运行上下文、模板与项目实例的产品语义

一句话：

- deer-flow 的 `thread` 是内部运行锚点
- SwarmMind 的 `ChatSession / Project / Agent Team` 是外部产品语义

## 3. SwarmMind 的前端对象模型

### 3.1 用户可见对象

- `ChatSession`
- `Project`
- `ProjectAgentTeamInstance`
- `Artifact`
- `Approval Item`

### 3.2 前端运行对象

- `runtime_thread_id`
- `run_id`
- `artifact_refs`
- `upload_refs`
- `subtask_refs`
- `stream_state`

### 3.3 映射原则

```text
ChatSession
  -> 1 primary deer-flow thread

Project
  -> 1 project workspace shell
  -> 1 current collaboration thread
  -> optional historical threads / run timeline

Agent Team
  -> not a route primary key
  -> visible as product role / mounted team instance
  -> internal runtime still maps to lead-agent + subagents
```

## 4. 应吸收的实现机制

### 4.1 `new -> real id` 切换不能导致主工作面重挂载

deer-flow 在新会话开始后，不使用框架路由强制重进页面，而是原地把 URL 从 `new` 切到真实 `thread_id`。

SwarmMind 应吸收这条原则：

- 创建新的 `ChatSession` 时，前端先生成临时本地 key
- 一旦后端返回正式 id，应原地替换 URL 与状态绑定
- 不能因为 id 变化让主消息区、输入区、artifact 侧栏整体 remount

否则会直接导致：

- 流式状态丢失
- 输入区状态闪断
- 产物侧栏关闭
- 运行中的子任务卡片消失

### 4.2 消息渲染必须按执行语义分组

SwarmMind 不应只渲染“人类一条、AI 一条”的普通聊天流。

至少应支持下列语义组：

- `human`
- `assistant response`
- `assistant reasoning`
- `tool / approval / clarification`
- `artifact presentation`
- `subagent / delegated task`

这条规则对 `ChatSession` 和 `Project 协作台` 都成立。

差别只是：

- `ChatSession` 更轻，展示更克制
- `Project 协作台` 更强调整轮运行、风险、审批和产物

### 4.3 artifact 不应离开当前工作面

deer-flow 的一个重要优点，是 artifact 与消息流处于同一工作空间。

SwarmMind 也应保持：

- 消息区是主叙事流
- 右侧面板承接 artifact、run detail、上下文和引用资料
- 用户不需要跳出会话页才能理解“一次运行产出了什么”

对 `Project 协作台`，右栏还应额外承接：

- 当前项目状态
- 相关审批状态
- 当前挂载 Team 实例摘要

### 4.4 上传、流式运行、subtask 必须共用同一上下文主键

上传不是独立小功能。

一旦文件被附加到当前会话，它必须和当前运行上下文绑定：

- 上传列表归属于当前 thread / session runtime
- 提交消息时附带文件引用
- 后续 artifact / run detail 可追溯这些输入

同理：

- subtask 卡片
- 计划模式中间态
- tool 执行状态

都应共享同一个运行上下文，而不是散落在多个 store。

## 5. SwarmMind 的页面骨架建议

### 5.1 ChatSession 页面骨架

```text
顶栏：标题 / 模式 / 轻量动作
主区：消息流
底部：输入框 / 附件 / 模式选择
右栏：可折叠 artifact / run detail / 引用资料
```

要求：

- 强调探索与快速发起
- 支持“提升为 Project”
- 不默认展示重治理信息

### 5.2 Project 协作台骨架

```text
项目顶栏：项目名 / 状态 / Team 实例 / 主动作
主区：项目消息流 / 执行语义流
右栏：artifact / 审批 / 风险 / 上下文 / run detail
底部：项目输入框 / 上传 / 模式切换
```

要求：

- 明显区别于普通聊天页
- 输入不只是追加聊天，而是推动项目状态机前进
- 相关结果需要回写 Overview / Kanban / Timeline / Artifacts

## 6. 不应照搬 deer-flow 的部分

### 6.1 不把 `thread` 直接暴露给用户

SwarmMind 界面、文档、导航和信息架构中，应继续使用：

- `ChatSession`
- `Project`
- `Agent Team`

而不是把产品对象替换成 `thread`、`assistant`、`subagent thread`。

### 6.2 不把 Agent 路由做成主信息架构

deer-flow 有 `/agents/[agent_name]/chats/[thread_id]` 这类路径。

SwarmMind 不应把“按 agent 进入聊天”做成主入口。

更合理的入口应该是：

- 先按 `ChatSession` 进入探索
- 或按 `Project` 进入正式协作
- `Agent Team` 作为工作上下文出现，而不是作为用户必须理解的运行时路由

## 7. 自动标题生成能力

### 7.1 deer-flow 的做法为什么值得复用

deer-flow 不是在创建 thread 时立刻生成标题，而是在首轮完整交换后生成：

- thread 还没有 title
- 已经出现 1 条 human message
- 已经出现至少 1 条 assistant message

然后由独立的 `TitleMiddleware` 调用模型生成标题，失败时再退回到用户首条消息截断。

这个时机是对的，因为：

- 只看用户第一句话，标题容易过宽或过散
- 加入 assistant 首轮响应后，模型已经理解该会话真正的意图
- 标题生成只做一次，避免会话标题在多轮对话中持续抖动

### 7.2 SwarmMind 应如何落地

SwarmMind 也应复用这条能力，但落在自己的控制面存储中。

建议规则如下：

- 标题归属 `ChatSessionStore`
- 不归属 `RunStore`
- 不仅存在于 deer-flow thread state
- 前端列表、最近记录、工作台卡片都读取同一份 `ChatSession.title`

建议最小字段：

```text
ChatSession
  - chat_session_id
  - thread_id
  - title
  - title_status        (pending | generated | fallback | manual)
  - title_source        (llm | fallback | manual)
  - title_generated_at
```

### 7.3 触发流程

```text
创建 ChatSession
  -> title 先为空或使用轻量占位文案
  -> 用户发送首条消息
  -> assistant 返回首轮响应
  -> 触发 title generation job
  -> 更新 ChatSessionStore.title
  -> 前端最近记录 / 页面标题 / 工作台卡片自动刷新
```

### 7.4 对当前数据库架构的含义

如果沿用当前 `conversations` 表的简化实现，下一步不应继续在创建会话时同步生成标题。

更合理的方向是：

- `POST /conversations` 只创建会话壳
- `POST /conversations/{id}/messages` 在首轮 assistant 响应完成后再尝试生成标题
- 标题写回 `conversations` 表，未来再平滑迁移到正式 `ChatSessionStore`

这意味着我们当前数据库至少应从“只有 `title` 文本字段”，升级为“有标题状态语义”的结构。

### 7.5 手动改名优先级

自动标题只负责生成初始可读标题。

后续规则应固定为：

- 手动标题覆盖自动标题
- 一旦进入 `manual`，系统不再自动重写
- Promote to Project 时，可把 ChatSession 标题作为 Project 名称建议值，而不是强制值

## 8. 最终设计原则

- `ChatSession` 是探索入口，不是弱化版产品
- `Project` 是唯一正式执行边界
- `Agent Team` 是产品层协作语义，不是独立前端 runtime
- deer-flow `thread` 是内部运行锚点，不是用户对象
- 会话页与协作台都应围绕统一运行上下文组织消息、artifact、upload、subtask 和 run detail
- UI 应优先表达执行语义，而不是普通聊天外观

## 9. 对当前前端实现的直接指导

SwarmMind 后续前端实现应按以下顺序推进：

1. 先定义 `ChatSession runtime state` 与 `Project collaboration runtime state`
2. 统一消息分组模型，而不是继续做纯聊天气泡列表
3. 为 `ChatSession` 与 `Project 协作台` 设计共享工作面骨架
4. 将 artifact / upload / run detail 收拢到同一上下文面板
5. 最后再接 Team、审批、项目状态回写

这条顺序很重要。

如果先做零散页面，再补运行主键和语义分组，后面会被迫重构两次。
