# SwarmMind 技术债偿还结论

> 文档类型: [B] 工程状态文档 - 债务收口结论
> 日期: 2026-04-15
> 适用阶段: v0.9.0 / Phase A 收口
> 口径: 本文档只记录当前结论，不再保留已过期的执行中间态

---

## 1. 结论

截至 2026-04-15，SwarmMind 当前**已经没有“非还不可”的技术债**。

前一轮集中偿还之后，主路径相关的高风险结构债已从“必须优先处理”下降为“可接受的受控复杂度”：

1. `supervisor.py` 已从集中式巨石收口为 app assembly + supervisor/system endpoint + route wiring
2. `general_agent.py` 的高耦合 stream capture / event normalization 已下沉到 `services/`
3. `v0-ai-chat.tsx` 已完成两轮拆分，展示组件与前端纯工具层已拆出
4. trace 已有 conversation-level orchestration、provider boundary 与 storage boundary
5. 关键主路径测试已补齐，当前全量测试稳定通过

因此，当前建议是：

- **停止主动还债**
- 仅在“阻塞新功能”或“制造真实故障”时，点状继续偿还

---

## 2. 本轮后的真实状态

### 已经完成的高价值债项

- `已完成` 消息 schema / ORM / repository 一致化
- `已完成` clarification 持久化旁路清理
- `已完成` trace endpoint orchestration 从 API 层下沉
- `已完成` sqlite checkpoint 查询与解析分层
- `已完成` `supervisor.py` conversation routes 抽离
- `已完成` `general_agent.py` stream event processing 下沉
- `已完成` `v0-ai-chat.tsx` 第一轮 UI 拆分
- `已完成` `v0-ai-chat.tsx` 第二轮纯工具层拆分
- `已完成` 主路径回归测试补强

### 当前主文件体量

- [`swarmmind/api/supervisor.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/api/supervisor.py): `480` 行
- [`swarmmind/agents/general_agent.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/agents/general_agent.py): `492` 行
- [`ui/src/components/ui/v0-ai-chat.tsx`](/Users/krli/workspace/SwarmMindProject/SwarmMind/ui/src/components/ui/v0-ai-chat.tsx): `1009` 行

### 最新验证基线

- `uv run ruff check swarmmind tests` 通过
- `cd ui && pnpm exec tsc --noEmit` 通过
- `make test` 通过
- 当前后端全量测试为 `143 passed`
- 当前 coverage 约 `86.43%`

---

## 3. 剩余债项分级

## 3.1 非必须立即处理

这些债项存在，但**当前不构成停工条件**。

### A. DeerFlow runtime bridge 仍是桥接模型

现状：

- [`swarmmind/services/runtime_bridge.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/runtime_bridge.py) 仍维护 `iter_async_generator_in_thread(...)` 与 `run_coroutine_blocking(...)`
- [`swarmmind/agents/general_agent.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/agents/general_agent.py) 仍通过桥接层兼容同步入口与流式入口

判断：

- 这是当前唯一还保留“补丁式执行模型”特征的区域
- 但它已经被局部封装，并有回归测试保护
- 只有在接下来要显著增强 `subagent`、取消恢复、长流式并发时，它才会重新上升为高优先级

结论：

- **现在不必继续处理**
- 如未来扩展 runtime 复杂度，再重启专项收口

### B. `working_memory` 物理表名遗留

现状：

- [`swarmmind/db_models.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/db_models.py) 已用 `SharedMemoryDB`
- 物理表名仍为 `working_memory`，目的是兼容既有 schema

判断：

- 这是语义债，不是运行债
- 当前没有第二套公开 repository 入口，也没有主路径混淆风险

结论：

- **延后处理即可**

### C. trace 仍依赖上游 `checkpoints` schema

现状：

- [`swarmmind/services/trace_checkpoint_storage.py`](/Users/krli/workspace/SwarmMindProject/SwarmMind/swarmmind/services/trace_checkpoint_storage.py) 仍读取上游 `checkpoints` 表
- 但查询、provider、service 已经分层

判断：

- 这是兼容债，不是边界失控
- 只有在上游 schema 真实变更或本项目要脱离该 schema 时，才需要继续处理

结论：

- **当前利息较低**

### D. `v0-ai-chat.tsx` 仍偏大

现状：

- [`ui/src/components/ui/v0-ai-chat.tsx`](/Users/krli/workspace/SwarmMindProject/SwarmMind/ui/src/components/ui/v0-ai-chat.tsx) 仍有约 `1009` 行

判断：

- 这已从“主路径结构债”降为“前端状态组织优化项”
- 当前没有证据表明它在阻塞功能交付或导致频繁缺陷

结论：

- **不作为当前主线债务**

---

## 4. 后续触发条件

只有满足以下任一条件，才建议继续还债：

1. 某项债直接阻塞新功能实现
2. 某项债开始制造真实线上或开发期故障
3. 某项债导致同一热区频繁返工

如果没有触发以上条件，则默认：

- 优先做功能
- 不再为“代码看起来还能更漂亮”而继续开还债回合

---

## 5. 当前建议

当前建议只有一句话：

**技术债专项可以收工，转回功能开发。**
