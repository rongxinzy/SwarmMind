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

  <img src="https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-Apache--2.0-green.svg?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/Phase-1-orange.svg?style=flat-square" alt="Phase">
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

---

##  supervisor UI

人类监督者界面，用于与 AI agent 团队交互：

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

**使用流程：** 打开 http://localhost:3000 → 提交目标 → 在 Pending 标签页审批/拒绝提案。

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

🟡 **Phase 1 — 核心完成**

构建最小可工作系统：
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
