# 多 LLM Provider 支持方案设计

> 状态：已实施  
> 实施日期：2026-04-26  
> 影响范围：Phase A/B 运行时层 + 控制面配置  

---

## 1. 现状分析

### 1.1 当前数据流

```
.env (单 provider)
  ↓
swarmmind.config.py  ──读取──►  LLM_PROVIDER / LLM_MODEL / LLM_API_KEY / LLM_BASE_URL
  ↓
swarmmind.runtime.catalog.infer_env_runtime_model()
  ↓ 推断 LangChain 类路径 (langchain_openai:ChatOpenAI 或 langchain_anthropic:ChatAnthropic)
swarmmind.runtime.catalog.sync_env_runtime_model()
  ↓ 写入/更新
RuntimeModelDB (sqlite/postgres) ──存──► name, provider, model_class, api_key_env_var, base_url
  ↓ 启动时读取
runtime/bootstrap.py._render_config()
  ↓ 生成 YAML
DeerFlow config.yaml ──models 列表──► name, use, model, api_key: $ENV_VAR, base_url
  ↓ 运行时解析
DeerFlow AppConfig.resolve_env_variables() ──os.getenv()──► 真实 API key
  ↓
DeerFlow models/factory.create_chat_model() ──动态 import──► LangChain 实例
  ↓
远端 LLM API
```

### 1.2 关键限制

| 限制 | 说明 |
|------|------|
| **单 Provider** | `sync_env_runtime_model()` 每次启动会把之前 env-sourced 的模型全部 disable，只保留当前环境变量的一个模型 |
| **API Key 不落地** | `RuntimeModelDB` 只存 `api_key_env_var`（字符串 `"OPENAI_API_KEY"`），不存真实 key；真实 key 在 DeerFlow 进程内通过 `os.getenv` 解析 |
| **DeerFlow 持钥** | config.yaml 中的 `$ENV_VAR` 在 DeerFlow 启动时被解析为明文，DeerFlow 进程直接持有各远端 API key |
| **无动态添加** | 新增 provider 必须改 `.env` 并重启整个服务栈 |
| **模型与供应端 1:1** | 一个 `RuntimeModelDB` 行对应一个 LangChain 类 + 一个 base_url + 一个 api_key_env_var |

### 1.3 litellm 现状

- **已安装**：`pyproject.toml` 中有 `"litellm>=1.82.6"`，基础 SDK 可用
- **Router 可用**：`litellm.Router` 支持多模型路由、fallback、重试、负载均衡
- **Proxy 不可用**：`litellm[proxy]` 需要额外依赖（`apscheduler` 等），当前未安装
- **Provider 覆盖**：litellm 支持 100+ provider，统一用 `provider/model` 格式调用

---

## 2. 核心问题

用户提出三个关键需求：

1. **多 Provider**：启动时可配置多个，也可运行时动态添加
2. **数据库存储**：provider 类型、base_url、api_key 至少落在数据库
3. **中间层隔离**：agent（DeerFlow）不应直接拿到真实远端 API key

这三个需求之间存在依赖关系：
- (3) 中间层隔离 → 必须改变 DeerFlow 直接持钥的架构
- (2) 数据库存储 → 需要扩展 `RuntimeModelDB` 或新建 provider 表
- (1) 多 Provider + 动态添加 → 需要热刷新机制，不能依赖重启

---

## 3. 方案对比

### 方案 A：直连扩展（不加中间层）

**架构**：扩展 `RuntimeModelDB`，增加 `api_key_encrypted` 字段。启动时/动态添加时写入多行。bootstrap 生成 config.yaml 时输出多个模型，DeerFlow 直连各 provider。

```
RuntimeModelDB (多行)
  ↓
config.yaml models: [openai-model, anthropic-model, azure-model, ...]
  ↓
DeerFlow 持各 provider 真实 key，直连远端
```

**优点**：
- 改动最小，和现有架构一致
- 不需要额外依赖
- DeerFlow 原生支持，无需改其内部逻辑

**缺点**：
- ❌ **不满足隔离需求**：DeerFlow 进程仍然持有所有真实 API key
- API key 加密存储增加复杂度（Fernet 密钥管理）
- 动态添加后需要重启 DeerFlow 才能刷新 config.yaml
- 每个 provider 需要不同的 LangChain 类，bootstrap 需要更复杂的类推断逻辑

**结论**：不推荐。用户的"中间层隔离"需求是明确的产品边界决策，不应绕过。

---

### 方案 B：litellm Proxy（独立服务）

**架构**：安装 `litellm[proxy]`，启动独立的 litellm proxy server（FastAPI + uvicorn）。SwarmMind 管理 proxy 的 `config.yaml`。DeerFlow 只配置一个模型：指向本地 proxy。

```
SwarmMind DB (provider 配置)
  ↓ 生成/刷新
litellm proxy server (port 4000)
  ↓ OpenAI-compatible API
DeerFlow config.yaml ──单一模型──► base_url=http://localhost:4000, api_key=proxy-master-key
  ↓
DeerFlow ChatOpenAI ──请求──► litellm proxy ──路由──► OpenAI/Anthropic/Azure/...
```

**优点**：
- litellm proxy 功能成熟：路由、fallback、重试、计费、监控、速率限制
- DeerFlow 侧改动极小：只需把 base_url 指向 proxy
- 社区生态完善，文档丰富

**缺点**：
- 引入 `litellm[proxy]` 的大量额外依赖（apscheduler、fastapi、uvicorn 等，可能和 SwarmMind 版本冲突）
- 多一个独立进程需要管理（启动、健康检查、重启）
- proxy 的配置格式和 SwarmMind DB 之间需要一层转换
- litellm proxy 的日志/监控/DB 可能和 SwarmMind 的控制面数据产生重叠或冲突
- 架构控制权部分外移到 litellm

**结论**：可行，但依赖较重，控制面边界不够清晰。

---

### 方案 C：SwarmMind LLM Gateway（推荐）

**架构**：在 SwarmMind FastAPI 应用内部实现一个轻量 Gateway sub-router，暴露 OpenAI-compatible `/gateway/v1/chat/completions` 和 `/gateway/v1/models` endpoint。Gateway 内部用 litellm SDK（`Router`）做请求路由。DeerFlow 的所有模型配置都指向这个 Gateway。

```
SwarmMind DB
├─ LlmProviderDB (provider_id, provider_type, api_key_encrypted, base_url, ...)
├─ LlmProviderModelDB (provider_id, model_name, litellm_model, capability flags)
└─ RuntimeModelDB (模型目录， capability_tags，不变)

         ┌──────────────────────────────────────┐
         │      SwarmMind FastAPI App           │
         │  ┌────────────────────────────────┐  │
         │  │  LLM Gateway (/gateway/v1/*)   │  │
         │  │  • /models                     │  │
         │  │  • /chat/completions           │  │
         │  │  • 内部 litellm.Router 路由    │  │
         │  └────────────────────────────────┘  │
         └──────────────────────────────────────┘
                      ↑ OpenAI-compatible API
DeerFlow config.yaml ─┘
  models:
    - name: gpt-4o
      use: langchain_openai:ChatOpenAI
      model: gpt-4o
      api_key: $SWARMMIND_GATEWAY_KEY
      base_url: http://localhost:8000/gateway/v1
    - name: claude-3-5-sonnet
      use: langchain_openai:ChatOpenAI
      model: claude-3-5-sonnet
      api_key: $SWARMMIND_GATEWAY_KEY
      base_url: http://localhost:8000/gateway/v1
```

**核心机制**：

1. **模型列表不变**：`GET /runtime/models` 仍然返回所有可用模型（从 `RuntimeModelDB` + `LlmProviderModelDB` JOIN 得到）。前端/用户看到的是 `gpt-4o`, `claude-3-5-sonnet` 等产品名。

2. **DeerFlow 统一走 Gateway**：bootstrap 生成的 config.yaml 中，所有模型的 `use` 都是 `langchain_openai:ChatOpenAI`（OpenAI-compatible），`base_url` 指向 SwarmMind Gateway，`api_key` 是一个 SwarmMind 生成的随机 proxy key。

3. **Gateway 路由**：收到请求后，根据请求中的 `model` 参数查 `LlmProviderModelDB` 获取 `litellm_model`（如 `openai/gpt-4o`），用 `litellm.Router` 调用真实 provider。

4. **Key 隔离**：
   - 真实 API key 加密存储在 `LlmProviderDB.api_key_encrypted`
   - 解密只在 SwarmMind 进程内存中进行
   - DeerFlow 只拿到 `$SWARMMIND_GATEWAY_KEY`，无法反向获取真实 key

5. **热刷新**：添加/修改 provider 后，SwarmMind 自动重建 `litellm.Router` 实例，无需重启 DeerFlow（因为 DeerFlow 始终指向同一个 gateway URL）。

**优点**：
- ✅ **满足隔离需求**：DeerFlow 完全不接触真实远端 API key
- ✅ **架构内聚**：Gateway 是 SwarmMind 控制面的组成部分，不是外部依赖
- ✅ **控制力完整**：可以在 Gateway 层加自定义逻辑（审批钩子、审计日志、计费、速率限制）
- ✅ **依赖轻量**：只用基础 `litellm`（已有），不需要 `litellm[proxy]`
- ✅ **动态管理**：添加 provider 后热刷新，无需重启 DeerFlow
- ✅ **技术栈一致**：FastAPI，和 SwarmMind API 同进程

**缺点**：
- 需要实现 Gateway 的 OpenAI-compatible API（但 litellm SDK 已经处理了大部分 provider 适配，Gateway 主要做请求转发）
- 需要管理 Fernet 加密密钥
- Gateway 成为单点，但 DeerFlow 本身就是单进程本地运行，此风险可控

**结论**：**推荐**。最符合用户"中间加一层"的意图，同时保持了架构控制力和技术栈一致性。

---

## 4. 数据模型设计

### 4.1 新建表

```python
class LlmProviderDB(SQLModel, table=True):
    """LLM 供应端配置。一个供应端账号（如 OpenAI、Anthropic、DashScope）对应一行。"""
    __tablename__ = "llm_providers"

    provider_id: str = Field(primary_key=True)  # uuid
    name: str  # 显示名，如 "OpenAI Production"
    provider_type: str  # "openai", "anthropic", "azure_openai", "gemini", "dashscope"...
    api_key_encrypted: str  # Fernet 加密后的 API key
    base_url: str | None = None
    is_enabled: int = Field(default=1)
    is_default: int = Field(default=0)
    created_at: datetime | None = Field(default_factory=utc_now)
    updated_at: datetime | None = Field(default_factory=utc_now)


class LlmProviderModelDB(SQLModel, table=True):
    """供应端可提供的模型。多对多：一个 provider 可提供多个模型，一个模型可由多个 provider 提供。"""
    __tablename__ = "llm_provider_models"

    provider_id: str = Field(foreign_key="llm_providers.provider_id", primary_key=True)
    model_name: str = Field(primary_key=True)  # 与 RuntimeModelDB.name 对齐
    litellm_model: str  # litellm 格式，如 "openai/gpt-4o", "anthropic/claude-3-5-sonnet-20241022"
    is_enabled: int = Field(default=1)
    created_at: datetime | None = Field(default_factory=utc_now)
```

### 4.2 现有表调整

```python
class RuntimeModelDB(SQLModel, table=True):
    """模型目录。只存模型元数据和能力标签，不存供应端凭证。"""
    # ... 现有字段不变 ...
    # 移除 api_key_env_var（由 LlmProviderDB 替代）
    # 可选：加 capability_tags JSON 字段替代当前布尔标志
```

### 4.3 关系

- `RuntimeModelDB` ←──1:N──→ `LlmProviderModelDB`（一个模型可由多个 provider 提供）
- `LlmProviderDB` ←──1:N──→ `LlmProviderModelDB`（一个 provider 可提供多个模型）

---

## 5. Gateway API 设计

### 5.1 端点

```
GET  /gateway/v1/models              → 返回可用模型列表（OpenAI-compatible format）
POST /gateway/v1/chat/completions    → 聊天补全（流式/非流式）
POST /gateway/v1/completions         → 文本补全（可选）
POST /gateway/v1/embeddings          → Embedding（可选，未来扩展）
```

### 5.2 请求处理流程

```
DeerFlow ChatOpenAI ──POST /gateway/v1/chat/completions──► SwarmMind Gateway
  Headers: Authorization: Bearer <SWARMMIND_GATEWAY_KEY>
  Body: { model: "claude-3-5-sonnet", messages: [...], stream: true }

Gateway:
  1. 校验 gateway key
  2. 查 LlmProviderModelDB：model_name="claude-3-5-sonnet" → litellm_model="anthropic/claude-3-5-sonnet-20241022", provider_id="xxx"
  3. 查 LlmProviderDB：provider_id="xxx" → 解密 api_key, base_url
  4. 调用 litellm.Router.acompletion(model="anthropic/claude-3-5-sonnet-20241022", api_key=..., api_base=..., ...)
  5. 流式/非流式返回给 DeerFlow
```

### 5.3 关键实现要点

- **litellm Router 缓存**：Gateway 初始化时构建 Router，provider 变更时重建
- **Fallback**：在 `LlmProviderModelDB.fallback_model_names` 中配置，Router 构建时注入 `fallbacks` 参数
- **Cooldown**：Router 配置 `allowed_fails=3`, `cooldown_time=60`，自动隔离连续失败的 deployment
- **RetryPolicy**：按错误类型配置重试次数（RateLimit=3, Timeout=2, InternalServer=2）
- **Provider 健康检查**：后台 async task 每 30 秒用 `httpx` ping provider 的 `/v1/models`，更新内存中的 `ProviderHealth`
- **错误透传**：litellm 返回的错误转换为 OpenAI-compatible error format
- **流式响应**：`StreamingResponse` + `application/json` line-by-line（OpenAI SSE format）
- **Timeout**：Router 默认 120s，健康检查 10s

---

## 6. 管理 API 设计

### 6.1 Provider CRUD

```
GET    /llm-providers              → 列出所有 provider（不返回 api_key）
POST   /llm-providers              → 创建 provider
GET    /llm-providers/{id}         → 单个 provider 详情（mask api_key）
PATCH  /llm-providers/{id}         → 更新 provider
DELETE /llm-providers/{id}         → 禁用 provider（软删除）
POST   /llm-providers/{id}/models  → 为 provider 添加可用模型
```

### 6.2 创建 Provider 请求示例

```json
POST /llm-providers
{
  "name": "DashScope OpenAI",
  "provider_type": "openai",
  "api_key": "sk-dashscope-xxx",
  "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "models": [
    { "model_name": "qwen3.5-plus", "litellm_model": "openai/qwen3.5-plus" },
    { "model_name": "qwen-vl-max", "litellm_model": "openai/qwen-vl-max", "supports_vision": true }
  ]
}
```

### 6.3 与现有 `/runtime/models` 的关系

- `/runtime/models` 仍然返回用户可选的模型列表（ capability_tags 等）
- 内部实现改为从 `RuntimeModelDB JOIN LlmProviderModelDB` 获取，只返回有可用 provider 的模型

---

## 7. 实施步骤

### Phase 1：数据层（约 1 天）

1. **新增表**：`LlmProviderDB`, `LlmProviderModelDB`（db_models.py）
2. **Alembic migration**：生成并修正 migration
3. **Repository**：`LlmProviderRepository`（CRUD + 加密/解密）
4. **Pydantic models**：`LlmProvider`, `LlmProviderCreateRequest`, `LlmProviderModelEntry` 等
5. **加密工具**：Fernet 封装（`swarmmind/utils/crypto.py`）
6. **测试**：repository 测试（加密/解密、CRUD、mask api_key）

### Phase 2：Gateway 层（约 1.5 天）

1. **Gateway Router 实现**：`swarmmind/llm_gateway/router.py`
   - `LlmGateway` 类：内部 litellm.Router、provider 配置加载、热刷新
   - `ChatCompletionRequest` / `ChatCompletionResponse` Pydantic models
2. **FastAPI routes**：`swarmmind/api/llm_gateway_routes.py`
   - `/gateway/v1/models`
   - `/gateway/v1/chat/completions`（流式 + 非流式）
3. **接入 supervisor**：在 `api/supervisor.py` 中 mount gateway router
4. **Gateway key 生成**：启动时生成随机 key，写入环境变量供 DeerFlow 使用
5. **测试**：Gateway API 测试（mock litellm Router）

### Phase 3：DeerFlow 集成（约 0.5 天）

1. **修改 bootstrap.py**：
   - 所有模型统一用 `langchain_openai:ChatOpenAI`
   - `base_url` 指向 `http://{API_HOST}:{API_PORT}/gateway/v1`
   - `api_key` 用 `$SWARMMIND_GATEWAY_KEY`
2. **修改 catalog.py**：
   - `sync_env_runtime_model()` 改为从 `LlmProviderDB` 读取所有 enabled provider 的模型
   - 废弃 `api_key_env_var`，改为 gateway 模式
3. **测试**：bootstrap 生成的 config.yaml 验证

### Phase 4：管理 API（约 1 天）

1. **REST endpoints**：`GET/POST/PATCH/DELETE /llm-providers`
2. **动态刷新**：provider 变更后自动重建 Gateway Router
3. **测试**：API 测试

### Phase 5：迁移与清理（约 0.5 天）

1. **.env 兼容性**：保留现有 `.env` 配置作为初始 provider 种子
2. **RuntimeModelDB 清理**：移除 `api_key_env_var` 字段（或保留兼容）
3. **文档更新**：AGENTS.md, 本设计文档归档
4. **全量回归测试**

**总估算**：约 4-5 天

---

## 8. 决策点

### 需要用户确认的问题

1. **加密方案**：API key 加密用 Fernet（对称）还是 HashiCorp Vault/KMS（外部）？
   - 建议：Fernet 足够，密钥通过 `SWARMMIND_ENCRYPTION_KEY` 环境变量传入

2. **Gateway key 策略**：
   - A. 每次 SwarmMind 启动生成新的随机 gateway key，DeerFlow 需要重新读取（当前流程需要重启 DeerFlow  anyway）
   - B. Gateway key 持久化到 DB，DeerFlow 始终用同一个
   - 建议：B，更稳定

3. **是否保留直连模式（fallback）**：
   - 如果 Gateway 故障，是否允许 DeerFlow 直连 provider？
   - 建议：Phase 1 不保留，保持架构清晰。Gateway 和 SwarmMind 同进程，故障概率相同。

4. **是否用 litellm Proxy 替代自建 Gateway**：
   - 如果用户更信任 litellm 的成熟度，可以改为方案 B
   - 但需要接受额外依赖和管理复杂度

---

## 9. 文件变更清单

| 文件 | 动作 | 说明 |
|------|------|------|
| `swarmmind/db_models.py` | 新增 | `LlmProviderDB`, `LlmProviderModelDB` |
| `swarmmind/models.py` | 新增 | Provider Pydantic models |
| `swarmmind/utils/crypto.py` | 新增 | Fernet 加密工具 |
| `swarmmind/repositories/llm_provider.py` | 新增 | Provider CRUD + 加密 |
| `swarmmind/llm_gateway/router.py` | 新增 | Gateway 核心路由逻辑 |
| `swarmmind/llm_gateway/models.py` | 新增 | OpenAI-compatible request/response models |
| `swarmmind/api/llm_gateway_routes.py` | 新增 | Gateway FastAPI routes |
| `swarmmind/api/llm_provider_routes.py` | 新增 | Provider 管理 API routes |
| `swarmmind/api/supervisor.py` | 修改 | Mount gateway + provider routers |
| `swarmmind/runtime/bootstrap.py` | 修改 | 所有模型指向 gateway |
| `swarmmind/runtime/catalog.py` | 修改 | 从 LlmProviderDB 读取模型 |
| `swarmmind/config.py` | 修改 | 加 ENCRYPTION_KEY，保留兼容 |
| `alembic/versions/` | 新增 | migration |
| `tests/` | 新增 | provider repo, gateway API, provider API 测试 |
| `docs/multi-llm-provider-design.md` | 归档 | 本文件 |

---

## 10. 附录：litellm 路由格式参考

```python
from litellm import Router

router = Router(
    model_list=[
        {
            "model_name": "gpt-4o",  # DeerFlow/Gateway 看到的名字
            "litellm_params": {
                "model": "openai/gpt-4o",  # litellm 内部路由标识
                "api_key": os.environ["OPENAI_API_KEY"],
                "api_base": "https://api.openai.com/v1",
            },
        },
        {
            "model_name": "claude-3-5-sonnet",
            "litellm_params": {
                "model": "anthropic/claude-3-5-sonnet-20241022",
                "api_key": os.environ["ANTHROPIC_API_KEY"],
            },
        },
        {
            "model_name": "qwen3.5-plus",
            "litellm_params": {
                "model": "openai/qwen3.5-plus",
                "api_key": os.environ["DASHSCOPE_API_KEY"],
                "api_base": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            },
        },
    ],
    fallbacks=[{"gpt-4o": ["claude-3-5-sonnet"]}],
    routing_strategy="simple-shuffle",
)

# 调用
response = await router.acompletion(model="gpt-4o", messages=[...], stream=True)
```
