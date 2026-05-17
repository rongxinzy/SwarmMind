# SwarmMind Connector Architecture

> Version: v1.0
> Date: 2026-05-17
> Status: Design + Initial Implementation (Feishu CLI)

## 1. 背景与调研结论

### 竞品对比

| 平台 | 集成方式 | 特点 |
|---|---|---|
| **Manus** | Connector = MCP 客户端 + 凭证管理层 | 每个 Connector 绑定到 Project，通过 UID 引用；用户一次性授权，凭证存在平台侧；Phase 1 目标：Connector + Skills 深度组合实现 SOP |
| **LangChain** | `@tool` 装饰器 / `BaseTool` 子类 | 工具是 Python 函数，docstring 即描述，schema 自动推导 |
| **CrewAI** | 同 LangChain 模式，但独立实现 | Agent 初始化时绑定 tools；框架根据描述路由 |
| **Agent Skills (Anthropic)** | SKILL.md 文件标准 | 32 个平台支持；会话启动只读 metadata（30 tokens），任务匹配才加载全文（800 tokens）；解决 MCP 的 token 爆炸问题 |

### CLI vs MCP Token 成本对比

MCP 的核心问题：大型 MCP 服务器（如 GitHub MCP）有 93 个工具定义，仅 schema 就消耗 ~55,000 tokens。  
lark-cli 等 CLI 工具：~200 tokens（model 知道如何调用 `--help`），按需加载。

**最佳实践（Claude Code 自身的选择）**：  
- CLI/Shell → 本地操作（git, gh, 文件操作）
- MCP → 结构化外部服务集成（远程 API，结构化 I/O）  
- Agent Skills → 程序性知识层（叠加在 CLI 和 MCP 之上）

### 飞书 CLI (lark-cli) 调研

- **仓库**: `github.com/larksuite/cli`，Go 编写，npm 分发（`@larksuite/cli`）
- **规模**: 200+ 命令，17 个业务域，覆盖 2500+ OpenAPI 接口
- **三层抽象**: Shortcuts（`+agenda`）→ API 命令（1:1 对应接口）→ Raw API（`lark-cli api GET ...`）
- **24 个 AI Agent Skills**: `lark-calendar`, `lark-im`, `lark-doc`, `lark-task`, `lark-event`（WebSocket 事件订阅）等
- **Agent 友好**: NDJSON 输出，`--no-wait`，`--as user/bot`，`--dry-run`，OS keychain 存凭证
- **并行方案**: `lark-openapi-mcp`（Node.js MCP 服务器，包装 Feishu OpenAPI），Beta 阶段，不支持文件上传/云文档直接编辑

**选择 CLI 连接器（而非 MCP 连接器）的原因**:  
`lark-cli` 专为 AI Agent 设计，命令经过真实 Agent 测试，有预置 Skills；`lark-openapi-mcp` 仍是 Beta。CLI 是第一个连接器的最稳健基础。

---

## 2. Connector 概念定义

**连接器（Connector）** 是 SwarmMind 的一等集成单元，将外部系统（协作平台、SaaS 工具、数据源）双向桥接到 SwarmMind 控制面：

```
外部系统
    ↓ (事件: webhook / WebSocket / polling)
    │
[Connector 进程]                    ← 独立进程，不嵌入 API Server
    ├── Ingress Adapter  →  SwarmMind REST API (dispatch / chat)
    ├── MCP Tool Server  ←  DeerFlow agents via RuntimeProfile.mcp_servers
    └── Heartbeat        →  SwarmMind REST API (connector status)
    │
SwarmMind 控制面
    ├── ConnectorDB       (配置, 加密凭证, 状态)
    ├── Connectors API    (CRUD, heartbeat)
    └── CLI               (swarmmind connector ...)
```

### 两个方向

1. **Ingress（外部 → SwarmMind）**: 飞书消息 → 创建 SwarmMind 对话 / dispatch 目标  
2. **Tool Provider（SwarmMind Agents → 外部）**: Agent 调用飞书 API（发消息、建文档、查日历）via MCP tools

---

## 3. 设计原则

1. **独立进程，控制面归属** — Connector 是独立进程（类似 DeerFlow），SwarmMind 存储元数据和凭证，不托管 Connector 的执行逻辑。

2. **HTTP-first** — Connector 调用 SwarmMind REST API，不直接访问数据库。

3. **MCP-native 工具暴露** — Connector 通过 FastMCP 暴露 MCP Server，DeerFlow Agents 通过 RuntimeProfile 的 `mcp_servers` 配置消费。

4. **事件驱动 Ingress** — Connector 订阅外部事件流（WebSocket / webhook），翻译为 SwarmMind dispatch 调用。

5. **凭证主权** — 外部 API 凭证存储在 SwarmMind 的 ConnectorDB（Fernet 加密），运行时通过环境变量注入 Connector 进程，不经由 DeerFlow 或 Agent。

6. **Manifest 驱动** — 每个 Connector 声明机器可读的 Manifest，描述能力、配置 schema、传输协议、版本。

7. **渐进式集成** — 不强制要求 Connector 同时支持 ingress 和 tool_provider；可以只做其中一种。

---

## 4. Connector Manifest

```yaml
name: feishu-cli
version: 1.0.0
description: Bridges Feishu/Lark to SwarmMind via lark-cli
transport: mcp_http
capabilities:
  - ingest         # 接收飞书事件，dispatch 到 SwarmMind
  - tool_provider  # 暴露飞书 API 为 MCP tools，供 Agents 使用
config_schema:
  - name: app_id
    description: Feishu app ID (from Feishu Open Platform)
    required: true
    secret: false
  - name: app_secret
    description: Feishu app secret
    required: true
    secret: true
  - name: mcp_port
    description: Port for the MCP tool server
    required: false
    default: "7070"
  - name: event_bot_name
    description: Bot name to filter @mentions
    required: false
    default: ""
```

---

## 5. 飞书 CLI 连接器设计

### 5.1 MCP Tool Bridge

Connector 启动一个 FastMCP 服务器（`streamable-http` 或 `stdio`），每个 tool 对应一条 `lark-cli` 子进程调用：

| MCP Tool | lark-cli 命令 | 说明 |
|---|---|---|
| `feishu_send_message` | `lark-cli im message +send` | 发送消息到指定 chat |
| `feishu_list_messages` | `lark-cli im message list` | 列出 chat 消息 |
| `feishu_get_chat_info` | `lark-cli im chat get` | 获取 chat 信息 |
| `feishu_create_doc` | `lark-cli doc documents create` | 创建飞书文档 |
| `feishu_get_doc` | `lark-cli doc documents get` | 获取文档内容 |
| `feishu_search` | `lark-cli search +query` | 全局搜索 |
| `feishu_get_agenda` | `lark-cli calendar +agenda` | 获取日历议程 |
| `feishu_create_task` | `lark-cli task tasks create` | 创建任务 |
| `feishu_list_tasks` | `lark-cli task tasks list` | 列出任务 |
| `feishu_run_command` | `lark-cli <cmd>` | 执行任意 lark-cli 命令（高级用法） |

**每次 tool call 启动一个短生命周期子进程**（lark-cli 是无状态 CLI，开销可接受）。  
凭证由 `lark-cli` 自身通过 OS keychain 管理。

### 5.2 事件监听器（Ingress）

```
[lark-cli event +listen --format ndjson]  ← 长生命周期子进程
         ↓ NDJSON lines
[FeishuEventListener]
         ↓ 解析 im.message.receive_v1 等事件
[SwarmMindClient.dispatch() / create_conversation()]
         ↓ 异步等待结果
[lark-cli im message +send] ← 回复到原 chat
```

事件路由规则（可配置）：
- `@bot mention` → `dispatch(goal=message_text)`
- Direct Message → `create_conversation` + `send_message`
- 其他类型 → ignore / log

### 5.3 与 DeerFlow RuntimeProfile 集成

Connector 启动后上报 `mcp_url`，SwarmMind 可自动在 RuntimeProfile 的 `mcp_servers` 中注册该 Connector：

```yaml
# DeerFlow config.yaml fragment（由 RuntimeProfile bootstrap 生成）
mcp_servers:
  - name: feishu
    url: http://localhost:7070/mcp
    transport: streamable-http
```

---

## 6. 数据模型

```python
class ConnectorDB(SQLModel, table=True):
    connector_id: str      # primary key ("feishu-prod")
    name: str              # human label
    connector_type: str    # "feishu-cli" | "slack-mcp" | ...
    version: str
    status: str            # "inactive" | "running" | "error"
    config_json: str       # JSON; secret fields Fernet-encrypted
    mcp_url: str | None    # http://host:port/mcp when running
    last_heartbeat: datetime | None
    created_at: datetime
    updated_at: datetime
```

---

## 7. API Endpoints

```
GET    /connectors                          列出所有连接器
POST   /connectors                          注册连接器
GET    /connectors/{connector_id}           获取连接器详情
PATCH  /connectors/{connector_id}           更新配置
DELETE /connectors/{connector_id}           删除连接器
POST   /connectors/{connector_id}/heartbeat 连接器上报健康状态
```

---

## 8. CLI 命令

```
swarmmind connector list                       列出所有连接器
swarmmind connector add <type> --id <id>       交互式注册连接器
swarmmind connector status <id>                查看连接器状态
swarmmind connector remove <id>                删除连接器

# 飞书专用命令
swarmmind connector feishu serve-tools [--id <id>] [--port 7070]
    启动 MCP tool 服务器（供 DeerFlow agents 使用）

swarmmind connector feishu listen-events [--id <id>]
    启动事件监听器（飞书消息 → SwarmMind dispatch）
```

---

## 9. 安全考虑

- **凭证存储**: `app_secret` 等敏感字段通过 Fernet 加密存储在 ConnectorDB
- **进程隔离**: Connector 是独立进程，不共享 API Server 内存
- **权限最小化**: `lark-cli auth login --domain im,doc,task` 只授权所需 scope
- **注入防护**: `lark-cli` 内置输入注入保护
- **无直接 DB 访问**: Connector 只调用 SwarmMind REST API

---

## 10. 未来连接器 Roadmap

| 连接器 | 类型 | 优先级 |
|---|---|---|
| `feishu-cli` | CLI connector | **P0（当前）** |
| `slack-mcp` | MCP connector | P1 |
| `github-mcp` | MCP connector | P1 |
| `notion-mcp` | MCP connector | P2 |
| `email-smtp` | Webhook connector | P2 |
| `custom-webhook` | Webhook connector | P2 |
