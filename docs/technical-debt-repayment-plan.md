# SwarmMind 技术债偿还计划

> 文档类型: [B] 工程状态文档 - 当前技术债偿还计划
> 日期: 2026-04-15
> 适用阶段: v0.9.0 / Phase A 收口
> 目标: 在不扩新平台范围的前提下, 先降低主路径复杂度、旁路持久化风险和运行时脆弱性
> 状态口径: 本文档已按 2026-04-15 当前代码状态更新, 用于区分已完成、进行中和未开始债项

---

## 1. 结论

当前 SwarmMind 的主要技术债, 不是“能力缺失”, 而是主路径已经形成后, 出现了以下四类成本持续上升点:

1. 数据模型与持久化边界漂移
2. 主路径编排文件过载
3. DeerFlow 异步桥接稳定性不足
4. 关键运行路径测试保护偏弱

截至 2026-04-15 的最新实况判断:

- P0 债项已基本完成: 消息 schema / clarification 持久化旁路 / 关键回归测试已有明显收口
- P1 债项已进入深水区: `supervisor.py`、`general_agent.py` 和 `v0-ai-chat.tsx` 都已开始拆分, 但还没有完全收口到最终形态
- P2 债项已开始偿还: `working_memory` 兼容入口已删除, trace provider 边界已建立, 但遗留表名与上游 schema 兼容面仍在

因此, 这份计划当前更准确的状态是: `P0 基本完成, P1/P2 持续收口中`.

状态图例:

- `已完成` = 债项目标已在代码路径中兑现, 当前文档只保留归档价值
- `进行中` = 已有明确收口动作, 但验收标准尚未全部满足
- `未开始` = 主要结构和风险仍按原症状存在

---

## 2. 优先级总览

### P0. 立即偿还

- `已完成` 消息模型 / ORM / migration 一致化
- `已完成` 关键路径测试补强

### P1. 结构债

- `进行中` 拆分 `swarmmind/api/supervisor.py`
- `进行中` 稳定 DeerFlow 流式桥接
- `进行中` 拆分前端 `ui/src/components/ui/v0-ai-chat.tsx`

### P2. 运行与遗留债

- `进行中` 统一 memory truth, 处理 `working_memory` 遗留路径
- `进行中` 清理框架弃用警告与连接资源警告
- `进行中` 降低 TraceService 对 DeerFlow 内部 SQLite schema 的直接耦合

### P3. 延后处理

- 与当前主路径无直接关系的平台化扩展
- 完整用户系统
- 通用 provider 管理后台
- 新的一层运行时抽象

---

## 3. `supervisor.py` 判断

结论: `swarmmind/api/supervisor.py` 应归类为 `P1 结构债`, 不是可接受的集中式实现。

当前状态更新:

- 已抽出 [`swarmmind/services/conversation_support.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/conversation_support.py)
- 已抽出 [`swarmmind/services/stream_events.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/stream_events.py)
- 已抽出 [`swarmmind/services/lifecycle.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/lifecycle.py)
- FastAPI 生命周期已迁移到 [`lifespan`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py#L124)
- 但 [`swarmmind/api/supervisor.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py) 当前仍有约 `685` 行, 仍同时承载路由、流式会话主循环、clarification 接口、trace 暴露和运行时绑定

证据:

- 文件规模虽已从计划起草时的 `1112` 行降到约 `685` 行, 但仍是高变更热区。
- 同文件同时承载应用生命周期与后台线程:
  - `lifespan()` [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py#L124)
  - `_cleanup_scanner()` [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py#L151)
- 同文件同时承载运行时目录与健康接口:
  - `health()` [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py#L245)
  - `ready()` [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py#L251)
  - `list_runtime_models()` [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py#L262)
- 同文件同时承载会话内持久化辅助与运行时配置解析:
  - `_persist_user_message()` 已迁至 [`conversation_support.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/conversation_support.py#L101)
  - `_persist_assistant_message()` 已迁至 [`conversation_support.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/conversation_support.py#L108)
  - `_resolve_runtime_options()` 仍留在 [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py)
- 同文件同时承载 DeerFlow 事件协议翻译、标题生成和 trace:
  - `_translate_general_agent_event()` 已下沉到 [`stream_events.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/stream_events.py#L104)
  - `_maybe_generate_conversation_title()` 已下沉到 [`conversation_support.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/conversation_support.py#L115)
  - `get_conversation_trace()` 仍暴露在 [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py)
- 会话主路径已经把 API 编排、运行时控制、标题生成、持久化集中在一个文件:
  - 非流式主循环 `send_message()` [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py)
  - 流式主循环 `_stream_conversation_message()` [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py)
  - clarification 接口 `respond_to_clarification()` [supervisor.py](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py#L652)

判断标准:

- 如果一个文件只是在“同一资源的多个 HTTP endpoint”上集中, 仍可接受。
- 但 `supervisor.py` 已跨越 API 层、应用生命周期、运行时控制、事件语义层、持久化辅助和标题副流程。
- 这已经不是简单的 controller 聚合, 而是“主路径 orchestration + infrastructure glue + protocol translation” 的混合体。

因此, 它不应继续作为默认扩展点。

---

## 4. 技术债清单

## 4.1 P0 - 消息模型与持久化边界漂移

状态: `已完成`

症状:

- 起草计划时, `tool_call_id` / `name` 仍存在“模型声明了、旁路单独写入、正常路径不一致”的问题
- clarification 响应曾依赖特例持久化实现
- API 层曾显式依赖这条旁路

风险:

- ORM 模型、Pydantic 模型、数据库 schema 和 repository 契约不一致
- 后续消息改动容易出现“能写不能读”或“某一条路径绕过约束”的隐性故障

目标:

- 把 `tool_call_id`、`name` 正式纳入 SQLModel / migration / API model
- 删除 raw SQL 旁路
- 把 clarification 视为正式消息类型而非特例

当前兑现情况:

- [`swarmmind/db_models.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/db_models.py) 和 [`swarmmind/models.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/models.py) 已正式包含 `tool_call_id` / `name`
- [`swarmmind/repositories/message.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/repositories/message.py#L25) 的统一 `create()` 已直接持久化这两个字段
- clarification 已经走统一 repository 写入路径 [`swarmmind/api/supervisor.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py#L667)

## 4.2 P1 - `supervisor.py` 结构过载

状态: `进行中`

症状:

- 生命周期、健康接口、模型目录、会话流式主循环、trace、clarification 全在单文件
- 同文件拥有多套辅助函数, 其中不少本质是 service 层职责

风险:

- 修改任一聊天细节时, 容易同时碰到运行时、存储、事件协议
- 代码 review 难以做局部推理
- 测试隔离成本高

目标:

- API 层只保留路由和入参/出参适配
- 会话编排、事件翻译、标题生成、启动清理迁出到独立模块

当前进展:

- 已抽出 conversation support / stream event / lifecycle 三个 service 模块
- 已抽出 [`swarmmind/services/conversation_execution.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/conversation_execution.py)
- `supervisor.py` 行数已明显下降
- 但尚未拆到 route module + conversation service 的目标边界, 仍不是“只保留路由装配”

## 4.3 P1 - DeerFlow 异步桥接补丁化

状态: `进行中`

症状:

- `DeerFlowRuntimeAdapter` 既做事件流消费, 又在同步接口中通过新线程和新 event loop 规避 loop conflict
- 注释已明确这是为了解决 `httpx / event loop` 绑定问题

风险:

- 并发问题难复现
- loop 生命周期和资源回收不可见
- 调试栈更深, 出错点更分散

目标:

- 统一流式与非流式执行路径
- 消除“同步接口内部再起 loop”的补丁式桥接
- 把异常与取消语义拉平

当前进展:

- 线程桥接逻辑已抽离到 [`swarmmind/services/runtime_bridge.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/runtime_bridge.py)
- 已增加对应回归测试 [`tests/test_runtime_bridge.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/tests/test_runtime_bridge.py)
- [`swarmmind/agents/general_agent.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/agents/general_agent.py#L427) 仍使用 `iter_async_generator_in_thread(...)`, 说明补丁式桥接还没有被架构性消除

## 4.4 P1 - 关键路径测试覆盖不足

状态: `已完成`

症状:

- 起草计划时, `general_agent` 流式路径、clarification 和 bridge 行为保护偏弱
- `supervisor.py` 复杂度远高于可放心重构的保护网
- `clarification_middleware.py` 与 `working_memory.py` 当时缺少有效测试保护

风险:

- 主路径热区越复杂, 每次迭代越依赖人工回归
- 结构重构时缺少行为回归网

目标:

- 优先补运行最复杂的路径, 而不是追平均覆盖率
- 为后续拆分 `supervisor.py` 和异步桥接重构提供回归保护

当前兑现情况:

- 已有 [`tests/test_clarification_middleware.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/tests/test_clarification_middleware.py)
- 已有 [`tests/test_clarification_persistence.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/tests/test_clarification_persistence.py)
- 已有 [`tests/test_runtime_bridge.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/tests/test_runtime_bridge.py)
- 已有 [`tests/test_general_agent_stream_bridge.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/tests/test_general_agent_stream_bridge.py) 与 [`tests/test_general_agent_stream_events.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/tests/test_general_agent_stream_events.py)
- 当前全量测试通过 `140 passed`, 覆盖率约 `85.20%`

## 4.5 P2 - 多套 memory truth 并存

状态: `进行中`

症状:

- `working_memory` 表与 repository 仍保留
- 同时存在 `shared_memory` 和 `layered_memory` 主路径

风险:

- 开发者先要判断“哪套 memory 才是真正主路径”
- 容易继续把新需求接到遗留接口上

目标:

- 明确当前 Phase A 的 memory 主路径
- 冻结或删除 `working_memory` 写入入口
- 补充迁移说明或兼容策略

当前状态说明:

- 兼容 repository `swarmmind/repositories/working_memory.py` 已删除
- 共享 KV 的 ORM 命名已从 `WorkingMemoryDB` 收口为 `SharedMemoryDB`, 但物理表名仍保持 `working_memory` 以兼容现有 schema
- 当前剩余问题主要是遗留表名与 Phase A / Phase B 内存语义并存, 不再是多一套公开 repository 入口

## 4.6 P2 - 框架与资源警告累积

状态: `进行中`

症状:

- 起草计划时, FastAPI 仍使用 `@app.on_event("startup")`
- 起草计划时, 代码中存在 `datetime.utcnow()` 弃用面
- 测试期间曾出现 SQLite connection `ResourceWarning`

风险:

- 后续升级 FastAPI / Python / SQLModel 的迁移成本继续上涨
- 警告量过大, 会掩盖真正的新问题

目标:

- 将生命周期迁移到 `lifespan`
- 统一使用 timezone-aware 时间
- 消除连接未关闭告警

当前进展:

- 生命周期迁移到 `lifespan` 已完成
- 代码中已不再看到 `datetime.utcnow()`
- 但 warning 面是否彻底收零、SQLite 连接告警是否完全消失, 目前没有单独的“已归零”验收记录, 因此本项保留为进行中

## 4.7 P1 - 前端聊天工作面单组件过载

状态: `进行中`

症状:

- `ui/src/components/ui/v0-ai-chat.tsx` 体量过大
- 协议类型、流式读取、错误处理、clarification 恢复、artifact 面板状态全部聚集

风险:

- 与后端 `supervisor.py` 一样, 已成为高频热区
- 任何交互改动都需要同时理解协议和 UI 状态机

目标:

- 拆为协议适配层、流式 hook、展示组件和侧栏状态模块

当前状态说明:

- [`ui/src/components/ui/v0-ai-chat.tsx`](/Users/krli/workspace/SwarmMindProject/SwarmMind/ui/src/components/ui/v0-ai-chat.tsx) 已从约 `2098` 行降到约 `1510` 行
- 已抽出 controls / message rendering / artifact layout 到独立组件
- 主状态机与流式编排仍集中在 `v0-ai-chat.tsx`, 这部分还需要后续继续下沉

## 4.8 P2 - TraceService 耦合 DeerFlow 内部存储

状态: `进行中`

症状:

- `trace_service.py` 直接读取 DeerFlow checkpoint SQLite 和上游内部表结构

风险:

- 上游 schema 一变, 轨迹功能直接失效
- 故障只会在运行期暴露

目标:

- 为 trace 增加适配层
- 把“读取上游内部 schema”改成可替换的 provider

当前状态说明:

- 已新增 [`swarmmind/services/trace_provider.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/trace_provider.py), 将 SQLite checkpoint 读取从 `TraceService` 本体中抽离
- `TraceService` 现在依赖 provider 边界, 而不是自己直接管理连接与查询
- 当前剩余问题是默认 provider 仍复用 DeerFlow / langgraph 的 `checkpoints` 表结构, 但耦合点已被局部封装

## 4.9 P3 - 架构承诺与落地面之间存在长期张力

状态: `延后处理`

症状:

- 架构文档已承诺 ChatSession -> Project 路线
- 当前多个页面仍为占位

处理原则:

- 这不是当前首批偿还对象
- 先清主路径结构债, 再继续做横向扩面

---

## 5. 分阶段偿还方案

## 第 1 阶段: 主路径止血

状态: `已完成`

目标: 先清除最容易制造“写入旁路”和“重构无保护”的债。

范围:

1. 统一消息 schema
2. 删除 clarification raw SQL 旁路
3. 补主路径测试

交付项:

- `MessageDB`、Pydantic `Message`、repository create/read 路径一致
- clarification 走统一 repository 写入路径
- 新增覆盖:
  - 流式消息完成并持久化
  - clarification 响应持久化
  - tool message 读取回放
  - 标题生成回填基本流程

验收标准:

- 不再出现“message 某字段只有 SQL 旁路能写”的情况
- `supervisor.py` 不再直接依赖特例持久化实现
- 关键聊天路径的新增测试能在重构前提供保护

实际结果:

- 已完成消息 schema 一致化
- 已移除 clarification 持久化旁路
- 已补上主路径关键回归测试

## 第 2 阶段: 拆 `supervisor.py`

状态: `进行中`

目标: 把主路径从巨石文件中拆出清晰边界, 降低 blast radius。

建议拆分边界:

- `swarmmind/api/routes/system.py`
  - `health`
  - `ready`
  - `models`
- `swarmmind/api/routes/conversations.py`
  - `create/list/get/delete`
  - `messages/stream`
  - `clarification`
- `swarmmind/services/conversation_service.py`
  - 会话编排
  - 消息持久化协调
  - runtime 绑定
  - 标题回填触发
- `swarmmind/services/stream_event_translator.py`
  - DeerFlow event -> UI stream event
- `swarmmind/runtime/lifecycle.py`
  - startup / cleanup scanner / runtime bootstrap

执行策略:

- 先按“搬运不改义”拆模块
- 再在新模块内继续收敛接口
- 最后再切 `FastAPI lifespan`

验收标准:

- `supervisor.py` 仅保留 app 组装与路由注册, 或被分解为多个 route 模块
- 会话主循环不再和启动清理逻辑同文件共存
- 单测可直接针对 service 层验证主流程

当前结果:

- 已抽出 conversation support / stream event / lifecycle
- 下一步仍需把会话主循环与路由装配进一步拆开

## 第 3 阶段: 运行时桥接收口

状态: `进行中`

目标: 把 DeerFlow 执行路径从补丁式线程桥接转为可维护模型。

范围:

- 审核 `general_agent.py` 的同步 / 流式双入口
- 统一 act 与 stream 的底层执行器
- 明确 event loop、取消、异常传播和资源回收语义

建议方向:

- 优先保留一种权威执行模型
- 非主模型做适配层, 不再复制第二套 loop 管理
- 为 runtime 错误定义更稳定的边界类型

验收标准:

- 不再需要在同步接口里临时创建新线程和新 event loop 规避冲突
- 流式和非流式的输出语义一致
- 针对 loop conflict 的回归测试存在

当前结果:

- 已完成 bridge 抽离与测试补强
- 尚未完成“去掉线程 + 新 loop 补丁”

## 第 4 阶段: 遗留收口

状态: `进行中`

目标: 清理对后续迭代持续制造认知成本的遗留结构。

范围:

1. 冻结或删除 `working_memory`
2. 清理弃用警告与 SQLite 连接告警
3. 降低 TraceService 对上游内部表结构的直接依赖
4. 拆前端 `v0-ai-chat.tsx`

验收标准:

- memory 主路径有单一事实来源
- 测试 warning 显著下降
- trace 的上游依赖被局部封装
- 前后端聊天主工作面都不再由单个巨石文件承载

当前阻塞:

- `working_memory` 公开兼容面已删除, 但表级遗留命名仍在
- Trace provider 已建立, 但默认 provider 仍读取上游 schema
- 前端聊天主状态机仍集中, 只是已完成第一轮拆分

---

## 6. 建议工单拆法

### EPIC 1. Message Consistency

状态: `已完成`

- 增加消息字段 migration
- 更新 SQLModel / Pydantic / repository
- 删除 raw SQL clarification 旁路
- 为 tool message 与 clarification 增加测试

### EPIC 2. Conversation Orchestration Refactor

状态: `进行中`

- 抽离 conversation service
- 抽离 stream event translator
- 抽离 runtime lifecycle
- 将 `supervisor.py` 缩减为 route assembly

### EPIC 3. Runtime Execution Stabilization

状态: `进行中`

- 统一 `act()` / `stream_events()` 执行内核
- 去掉线程 + 新 loop 补丁
- 增加并发与取消测试

### EPIC 4. Legacy Surface Reduction

状态: `进行中`

- 处理 `working_memory`
- 处理 warnings
- 处理 trace 适配层
- 拆前端聊天巨石组件

---

## 7. 不建议当前优先做的事

- 完整用户系统
- 通用 provider 配置后台
- 进一步抽象新的执行引擎
- 为占位模块继续铺横向 UI

原因:

- 这些事项不会降低主路径复杂度
- 它们会与当前结构债叠加, 使每个新增功能的单位成本继续上升

---

## 8. 完成定义

本计划不以“平均覆盖率数字”或“warning 清零”作为唯一完成标准, 而以下列结果作为完成定义:

1. 消息持久化不再存在 ORM 外旁路
2. 会话主路径拥有稳定回归测试
3. `supervisor.py` 不再承担多层混合职责
4. DeerFlow 运行桥接不再依赖补丁式线程 + event loop 方案
5. memory / trace / warnings 的遗留面被明确收口, 不再继续扩散

---

## 9. 与现有计划的关系

- 本文档补充 `docs/chat-mainline-execution-plan.md` 的工程偿债维度
- `docs/chat-mainline-execution-plan.md` 回答“下一阶段先做什么功能主线”
- 本文档回答“为了让那条主线继续可演进, 必须先还哪些债, 以及按什么顺序还”

两者关系:

- 主路径执行计划决定产品顺序
- 技术债偿还计划决定工程收口顺序
