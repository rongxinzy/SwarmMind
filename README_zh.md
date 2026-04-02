<!-- Hero Tagline + Language Switcher -->
<p align="center">
  <h1>🤖 SwarmMind · 智能涌现</h1>
  <strong>智能从协作中涌现。</strong><br>
  <em>AI agent 团队是主体，人类是裁判。</em>
  <br><br>
  <a href="README.md">🇺🇸 English</a>
</p>

<!-- Badges -->
<p align="center">

  <a href="https://github.com/rongxinzy/SwarmMind/actions/workflows/ci.yml">
    <img src="https://github.com/rongxinzy/SwarmMind/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-Apache--2.0-green.svg?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Phase-1-orange.svg?style=flat-square" alt="Phase">
  <img src="https://img.shields.io/badge/Phase-2a-dev-yellow.svg?style=flat-square" alt="Phase 2a">
  <img src="https://img.shields.io/badge/AI%20Native-OS-black.svg?style=flat-square" alt="AI Native OS">
  <img src="https://img.shields.io/badge/架构-上下文broker-purple.svg?style=flat-square" alt="Architecture">

</p>

---

## 问题的本质

我们正在建造的所有工具，本质上都在做同一件事：**让人更好地完成知识工作。**

但有一个更深层的问题我们从来没有认真回答过：

> **如果知识工作本身不再需要人来做，会怎样？**

这不是"AI 辅助人类工作"。这是 **AI agent 成为工作主体，人类退到监督者和决策者** — 不是旁观者，是裁判，不是选手。

智能涌现是对这个问题的回答。

---

## 旧范式 → 新范式

| 工具 | 旧范式（人在做，AI 帮一点） | 新范式（AI agent 做，人监督） |
|------|---------------------------|---------------------------|
| **项目管理** | Jira — 人建 ticket、分配任务 | SwarmMind — AI 路由目标、填补上下文缺口 |
| **知识库** | Confluence — 人写文档、搜索文档 | AI agent 共享上下文，LLM 按需生成视图 |
| **通信** | Slack — 人发消息、等人回复 | Agent 写共享上下文，无收件箱 |
| **代码审查** | GitHub PR — 人手动 review | AI agent 协作审查、自我改进 |

**根本转变：** *"人类是主角，AI 是助手"* → ***AI agent 团队是主角，人类是裁判。***

## 企业应用场景

SwarmMind 改变了大规模企业的运作方式：

| 应用场景 | 替代了什么 | 价值 |
|----------|-----------|------|
| **自动化定期简报** | 周报、月度 P&L 汇报 | 始终最新、零人工汇总 |
| **异常告警** | 异常报表、关键指标预警 | 主动发现——识别人类遗漏的模式 |
| **跨系统调研** | "这个我得问 5 个部门" | 一个问题，跨所有系统聚合答案 |
| **深度专项调查** | 数天的反复沟通 | 几分钟——AI 读完所有材料，精准回答 |

---

## 什么是 SwarmMind

SwarmMind 是一个 **给 AI agent 团队用的操作系统** — 不是消息队列，不是工作流引擎，不是又一个"AI 助手"。它是 **企业认知基础设施**。

操作系统的核心洞察：**多个独立的实体，不需要知道彼此的存在，就能协作** — 它们通过共享资源来协调。

```
┌─────────────────────────────────────────────────────────────┐
│                     你（人类监督者）                         │
│              "这个项目现在什么状态？"                         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│               LLM 状态渲染器                                 │
│     ┌───────────────────────────────────────────────────┐   │
│     │  按需生成：表格？甘特图？prose？— LLM 临场决定   │   │
│     └───────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ 从上下文读取一切
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    CONTEXT BROKER                           │
│         协调者：把目标分发给对的 agent                        │
└──────┬──────────┬──────────┬──────────┬───────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
   ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
   │  财务   │ │  客服   │ │  代码  │ │  产品   │
   │  Agent │ │  Agent │ │  审查  │ │  数据   │
   └────────┘ └────────┘ └────────┘ └────────┘
                   │
                   ▼
        ┌──────────────────────┐
        │   SHARED CONTEXT     │
        │  （所有 agent 读写     │
        │   同一份记忆）         │
        └──────────────────────┘
```

**为什么不是消息传递？** 想象两个专家在同一个房间里——不需要互发邮件，共享白板就够了。SwarmMind 就是给 AI agent 团队的"共享房间"。

**给企业 — AI 能力的"最后一公里"连接器"**

硅谷在搭建通用 AI 框架，我们解决的却是另一个问题：把你现有的企业数据，连接到真正能投产的 AI 能力上。

大多数企业的数据散落在 OA 系统、CRM、财务、HR、老旧平台里——但 AI 项目往往卡在 PoC 阶段，因为没有人解决数据接入、权限管控和运营工作流的"最后一公里"。SwarmMind 就是这座桥：通过 MCP/Skills 协议聚合内部数据，添加治理和审计管控，让你的团队——尤其是那些不写代码的决策者——能用调研对话的方式，真正激活那些数据。

**信息衰减的问题**

在传统公司里，来自一线的资讯要数周才能到达 CEO——层层过滤、汇总成 PPT、细节尽失。等到决策者看到的时候，信息已经失真：异常被正常化、上下文消失、预警信号被平滑成了定期报表。

这不是沟通问题——是结构性问题。分配权力的汇报层级，同时也过滤了信息。

看清这一点的人正在行动（扎克伯格据说正在打造一个能穿透企业层级的个人 AI，就是一个信号）——直接获取原始数据。SwarmMind 让每家公司都能做到这一点。你的领导团队可以问：

- *"本月毛利率下降的原因是什么？"*
- *"客户流失有哪些共同模式？"*
- *"哪些项目落后了，原因是什么？"*

不是静态看板，不是定时报表。这是与你整个组织数据的实时对话——可以深入追问、可以质疑、可以层层深挖。

**企业级基础架构**

SwarmMind 从第一天起就是按生产级标准构建的：系统调用和 MCP 权限边界、数据分类、审计日志、关键操作的回滚支持。安全不是事后补救。

---

## Supervisor UI

人类监督者界面，用于与 AI agent 团队交互——侧边栏导航，聊天优先体验：

- **Tasks**（默认）— 与 agent 团队对话。消息根据关键字路由到对应的专业 Agent，不匹配的消息由 LLM Status Renderer 直接回答。
- **Projects / Search / Agents / Library** — Phase 2 预留。

![SwarmMind Supervisor UI](ui/public/screenshot.png)

---

## 状态即上下文：不用 Jira 的方式做项目管理

Jira 把"工作状态"变成数据库里的 record：`ticket.status = "In Progress"` — 僵化、强制、逼你把工作塞进 4 种状态。

**现实工作从来不按 4 状态流转。** 一个设计迭代可能同时是"草稿"、"review"、"客户等待中"和"部分实现"——但 Jira 逼你选一个。

### 智能涌现的答案：

> **状态不是数据。状态是上下文。**

当你给 agent 一个"写季度财务报告"的目标，不需要 ticket 系统。agent 需要：
- **当前已有的是什么？** → 已有上下文
- **还缺的是什么？** → 上下文缺口探测
- **缺口由谁来填？** → 路由到对的 agent

当所有缺口都被填满，报告自然写出来了。**没有 "In Progress"，没有 ticket，没有 sub-task。**

人类问"项目现在什么状态？" → LLM 从共享上下文读取一切 → 生成最合适的视图（表格、甘特图、或一段话），**形式由 LLM 根据上下文临场决定**。

---

## 自进化：让团队自己变聪明

现有所有 AI 系统都有一个缺陷：**每次对话都是全新的开始**。不管用多少次 ChatGPT，它永远不会记住上次哪里做得好、哪里做得不好。

智能涌现通过**策略表**解决这个问题：

```
 情况                     路由到        成功率
──────────────────────────────────────────────────────────
"季度财务报告"             → 财务 agent    92%
"Python 代码审查"          → 代码 agent    87%
"客户投诉"                → 客服 agent    71%  ← 需要改进
"竞品分析"                → ???          0%  ← 新情况，需要新 agent
```

系统会观察：哪种情况 → 路由到哪个 agent → 人类批准还是拒绝 → 达到目标了吗？

基于这些观察，系统**自动更新路由策略**——人类监督，即时生效，完全可审计。

**不是微调（fine-tuning）。这是可审计的、人类可控的、即时生效的学习。**

---

## 为什么是开源的

因为这是**你企业大脑的基础设施**。没有人会把自己企业的"认知中枢"托付给一个黑盒系统。

更重要的是：开源社区会让这个系统变得更好。全世界的工程师会贡献新的 agent 类型、新的学习算法、新的协作模式。

**geek 精神：** 这件事本身是极客才会觉得激动的东西——让 AI agent 团队真正像团队一样协作、自进化、涌现智能。这不是"又一个 SaaS 工具"，这是对知识工作本质的重新思考。

---

## 路线图

| 阶段 | 重点 | 状态 |
|------|------|------|
| **Phase 1** | 核心系统：多 agent 路由、共享上下文、监督审批流程 | ✅ 已完成 |
| **Phase 2a** | **协作轨迹可见化** — 任务完成后回放完整推理过程 | 🚧 开发中 |
| **Phase 2b** | **实时协作 + 人工干预** — SSE 实时推送、干预消息、用户体系 | 📋 计划中 |
| **Phase 3** | **动态 Agent 上线 + 自主模式** — 系统自动发现新 agent，高置信度任务自动执行 | 📋 计划中 |
| **Phase 2c** | **企业数据连接器** — 面向常见企业系统（OA、CRM、财务）的预置 MCP 集成 | 📋 计划中 |
| **Phase 3b** | **私有 Skills 市场** — 企业可扩展 Agent 能力的白名单插件生态系统 | 📋 计划中 |

### Phase 2a: 协作轨迹可见化

> 与单轮 chat 的核心区别：用户**能看到团队是怎么思考的**。

每个 agent 在执行过程中将推理步骤写入 `event_log`。任务完成后，用户可以回放完整协作时间线——每步可展开，每一步思考都可见。

```
用户提交任务
       │
       ▼
  Context Broker 路由目标
       │
       ▼
  Agent A (财务) — 思考中... ──▶ event_log: 推理步骤 1
       │                                           │
       ▼                                           ▼
  Shared Memory 写入                            event_log: 推理步骤 2
       │                                           │
       ▼                                           ▼
  Agent B (代码审查) — 思考中...             event_log: 推理步骤 3
       │
       ▼
  任务完成 → 用户回放完整轨迹（可展开时间线）
```

**Phase 2a 交付内容：**
- `event_log` schema 扩展（reasoning、status、parent_event_id）
- `GET /tasks/{id}/trace` API — 完整协作历史
- 回放界面 — 逐步播放，可配置速度
- 公开任务链接（基于 UUID，无需登录）

### Phase 2b: 实时协作 + 人工干预

> 观看团队工作。只在关键时候介入。

SSE 实时流将 agent 推理过程推送到浏览器。人类可以随时注入指导消息——agent 收到后作为额外上下文参考，决定是否采纳。

**Phase 2b 新增：**
- SSE 实时流（`GET /tasks/{id}/stream`）
- 人工干预 API（`POST /tasks/{id}/guidance`）
- 每任务最多 3 次干预（防止过度干预）
- 用户账户 + 会话管理
- 用户任务历史

### Phase 3: 动态团队自进化

- 系统发现"未知情况" → 提案新 agent 类型
- 人类审批通过 → agent 自动注册到策略表
- 高置信度任务（历史成功率 >90%）自动执行，无需审批
- Phase 3 是团队真正**自进化**的时刻

---

## Phase 1 目标

> "看，这是一个 AI agent 团队，它们在协作完成知识工作，而且它们在从每次工作中学习，变得更好。问它们项目进行到哪了，它们会给你一个 AI 实时生成的回答，而不是一张 Jira 表格。"

| # | 组件 | 描述 |
|---|------|------|
| 1 | **两个专业 Agent** | 财务问答 agent + 代码审查 agent |
| 2 | **共享上下文层** | 所有 agent 读写同一份记忆 |
| 3 | **Context Broker** | 把人类的目标分发给对的 agent |
| 4 | **LLM 状态渲染器** | 按需生成状态总结（prose/表格/甘特图） |
| 5 | **人类监督界面** | 观察、批准、拒绝每个决定 |
| 6 | **策略表** | 记录路由规则，追踪成功率 |

---

## 快速开始

**环境要求：** Python 3.11+，Node.js 18+，npm

```bash
# Clone 仓库
git clone https://github.com/rongxinzy/SwarmMind.git
cd SwarmMind

# 配置密钥
cp .env.example .env
# 编辑 .env 填入你的 ANTHROPIC_API_KEY 和 ANTHROPIC_BASE_URL

# ========== 后端（使用 uv 管理 Python 环境）==========
uv sync                    # 安装 Python 依赖（推荐用 uv，比 pip 更准更快）

# 首次运行自动初始化数据库
uv run python -m swarmmind.api.supervisor
# API 运行在 http://localhost:8000

# ========== 前端（新终端）==========
cd ui
npm install                # 安装 Node 依赖
npm run dev                # 开发模式，热重载
# UI 运行在 http://localhost:3000
```

**为什么用 uv？** uv 是极速 Python 包管理器（比 pip 快 10-100 倍），同时管理项目依赖和虚拟环境，确保依赖一致性。

**使用流程：** 打开 http://localhost:3000 → 选择或创建对话 → 输入问题。匹配关键字的消息会路由到财务或代码审查 Agent，否则由 LLM 直接回答。

---

## 架构

| 层级 | 组件 | 职责 |
|------|------|------|
| **人类接口** | Supervisor UI (shadcn/ui) + LLM 状态渲染器 | 提交目标、审批/拒绝、查看状态 |
| **编排层** | Context Broker | 通过策略表路由目标到对的 agent |
| **Agent 层** | 财务 Agent、代码审查 Agent | 带 LLM 推理的专业领域行动者 |
| **记忆层** | 共享上下文（SQLite KV） | 持久化共享内存，冲突解决 |
| **监督 API** | FastAPI REST API | 人类监督和审批端点 |

---

## 项目状态

🟡 **Phase 1 — 已完成** | 🚧 **Phase 2a — 开发中**

### Phase 1 — 已完成
- [x] 项目概念与设计
- [x] Context Broker 实现
- [x] 财务 + 代码审查 Agent
- [x] 共享上下文层（SQLite KV）
- [x] Supervisor REST API（6 个端点 + 分页）
- [x] Supervisor UI（React + shadcn/ui，3 个标签页）
- [x] LLM 状态渲染器
- [x] 策略表 + 成功率追踪
- [x] Action proposal 超时机制（5 分钟）
- [x] 核心测试
- [x] 对话功能（流式输出 + 会话持久化 + LLM 生成标题）

### Phase 2a — 开发中
- [ ] `event_log` schema 扩展（reasoning、status、parent_event_id）
- [ ] `act()` 返回 EventLogEntry 与 ActionProposal
- [ ] `GET /tasks/{id}/trace` API
- [ ] 回放界面（时间线 + 可展开步骤 + 播放控制）
- [ ] 公开任务链接分享（基于 UUID，无需认证）

---

## 贡献

欢迎贡献。这是一个 AI 原生基础设施的开放实验。

- Fork 仓库
- 阅读[设计文档](./docs/design.md)了解架构
- 提交大型 PR 前先开 issue 讨论

---

## 许可证

Apache 2.0 — 见 [LICENSE](LICENSE)

---

<p align="center">

🇺🇸 <a href="README.md">English</a>

*SwarmMind · 智能涌现 — 让智能从协作中涌现。*

</p>
