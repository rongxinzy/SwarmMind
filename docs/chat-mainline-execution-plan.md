# SwarmMind ChatSession 主路径执行计划

> 文档类型: [B] 工程状态文档 - 当前执行计划
> 日期: 2026-04-14
> 适用阶段: v0.9.0 / Phase A 收口
> 结论: 先做 ChatSession 主路径闭环, 再做最小 DeerFlow 深集成, 再做精选多模型支持, 暂缓用户系统

---

## 1. 目标

本计划用于回答一个具体问题:

**SwarmMind 当前下一阶段应该优先做什么, 才能最快把产品从“能演示”推进到“有主路径可用”。**

最终决策:

1. 优先推进 `ChatSession -> DeerFlow 执行 -> 状态可见 -> 结果沉淀 -> Promote to Project` 主路径
2. DeerFlow 深集成只做服务于主路径的最小闭环, 不单开平台工程
3. 多模型 provider 支持做成“精选能力层”, 不做通用 provider 后台
4. 用户系统延后, 直到 Project 空间和协作治理面真正进入可交付状态

---

## 2. 为什么现在不是先做用户系统

当前代码和产品状态有一个明显事实:

- `ChatSession` 是真实工作入口
- `Projects / Teams / Skills / Assets / Knowledge / Schedules` 仍以占位页为主
- Phase A 在架构上强调的是 `ChatSession + Project + DeerFlow Gateway foundation`

因此当前瓶颈不是“谁能登录”, 而是“登录之后有没有一条值得走完的工作路径”。

如果主路径还没有跑通, 用户系统只是在半成品大厅外面加门禁。

---

## 3. 当前现状判断

### 3.1 已有能力

- 前端已有 `Workbench`、`最近会话`、`V0Chat` 主工作面
- 后端已有对话持久化、流式事件、标题生成、模式切换
- DeerFlow 已经嵌入执行链路, `flash / thinking / pro / ultra` 已映射到运行参数
- Runtime catalog 已有基础骨架, 支持模型列表、默认模型、匿名 subject 分配
- 测试当前通过: `70/70`

### 3.2 真实缺口

- 产品主舞台仍然过度集中在单页聊天, 尚未闭环到 `Promote to Project`
- 占位模块太多, 横向扩展会稀释当前最需要打磨的核心体验
- DeerFlow 的 `plan_mode / subagent / artifact / trace` 已部分接入, 但用户侧的可见性和可理解性还不够强
- 多模型是“已有骨架未产品化”, 用户系统则仍是“概念先行, 工程未落地”
- 测试通过但有大量技术债信号:
  - SQLite `ResourceWarning`
  - `datetime.utcnow()` 弃用警告
  - FastAPI `on_event` 弃用警告

---

## 4. 方向排序

### P0. ChatSession 主路径闭环

这是第一优先级, 不是继续做视觉 polish, 而是做成真正可工作的产品主路径。

### P1. 最小 DeerFlow 深集成

只做能直接增强主路径价值的集成:

- 规划模式更清晰
- 子代理协作更可见
- artifact 和 trace 更可读
- clarification 更顺滑

### P2. 精选多模型支持

只做用户真正感知得到的能力差异:

- 快速模型
- 深度模型
- 计划执行模型

不做:

- 完整 provider 管理后台
- 复杂 API key 管理页面
- 租户级模型矩阵设计

### P3. 其他模块

仅推进一个最小切片:

- `Promote to Project`

其他模块继续保留为架构承诺, 不作为当前迭代主目标。

### P4. 用户系统

在以下条件满足前不进入主线:

- Project 空间不再是占位页
- Promote to Project 已可用
- 至少存在一个需要成员、权限、历史归属的真实协作场景

---

## 5. 本次执行范围

## 5.1 In Scope

- 完成 ChatSession 主路径闭环
- 完成主路径所需的最小 DeerFlow 深集成
- 完成最小 `Promote to Project` 切口设计和第一版实现计划
- 为后续多模型支持预留产品位和数据位

## 5.2 Not In Scope

- 完整用户注册/登录/找回密码/组织管理
- 全量 RBAC
- Teams / Skills / Knowledge / Schedules 页面实装
- 通用 provider 管理台
- 多租户配置平台
- 重新设计第二套执行内核

---

## 6. 执行原则

1. **主路径优先于横向扩面**
   先把一个入口做深做透, 再补平台边缘。

2. **功能优先于视觉修饰**
   页面 polish 必须服务于“更可理解、更可恢复、更可操作”。

3. **DeerFlow 是执行内核, 不是展示负担**
   任何深集成都必须转化为用户可理解的工作状态, 而不是暴露底层术语。

4. **多模型先做产品抽象, 不先做平台抽象**
   用户关心的是“快 / 深 / 能规划”, 不关心 provider 配置表。

5. **用户系统只在负载真实协作需求时启动**
   不提前为假想复杂度付成本。

---

## 7. 里程碑

## M1. ChatSession 主路径闭环

### 目标

让 `V0Chat` 成为一个可以连续使用的真实工作面, 而不是只会流式吐字的 demo。

### 交付内容

- 对话创建、切换、删除、恢复完整稳定
- 模式切换 `flash / thinking / pro / ultra` 语义清晰
- 模型选择器具备真实可用性, 不是仅显示当前值
- 运行状态、推理、子任务、clarification、artifact 在同一工作面清晰呈现
- 错误、重试、空状态、加载状态完整
- 右侧上下文区和最近记录与当前会话保持一致

### 建议落点

- `ui/src/components/ui/v0-ai-chat.tsx`
- `ui/src/App.tsx`
- `swarmmind/api/supervisor.py`

### 验收标准

- 新建会话后不因真实 id 返回而整页重挂载
- 刷新页面后能恢复最近一次会话
- 流式执行期间用户能看懂“现在在干什么”
- 失败后有明确反馈, 并能重新发起
- `pro / ultra` 与 `flash / thinking` 的差异用户可感知

### 预估

- 人类团队: 4-6 天
- CC + gstack: 0.5-1 天

---

## M2. DeerFlow 最小深集成

### 目标

把 DeerFlow 的关键能力从“后台存在”变成“前台可感知且可控”。

### 交付内容

- 将 `plan_mode`、`subagent_enabled` 的差异映射为稳定的前端状态语言
- 强化 task / subtask / clarification / artifact 的事件展示
- 增强 trace 可读性, 让用户能回看一次执行发生了什么
- 统一运行事件到 UI 语义层, 避免直接暴露 DeerFlow 内部细节

### 建议落点

- `swarmmind/agents/general_agent.py`
- `swarmmind/api/supervisor.py`
- `swarmmind/services/trace_service.py`
- `ui/src/components/ui/v0-ai-chat.tsx`

### 验收标准

- `ultra` 模式下的子任务协作不是“黑箱”
- clarification 中断与续跑体验自然
- 产物和轨迹可以作为后续 `Promote to Project` 的输入
- 用户不需要理解 DeerFlow 术语, 也能理解系统行为

### 预估

- 人类团队: 3-5 天
- CC + gstack: 0.5-1 天

---

## M3. 最小 Promote to Project

### 目标

完成从探索入口到正式执行边界的第一刀, 让架构文档里的主线真正开始落地。

### 交付内容

- 在 ChatSession 中出现明确的 `Promote to Project` 触发点
- 提升时生成最小项目骨架:
  - 标题
  - 目标摘要
  - 范围
  - 约束
  - 来源会话引用
- 原 ChatSession 保留为只读来源记录
- Project 页即便仍简化, 也必须承接真实数据而不是纯占位

### 建议落点

- `swarmmind/repositories/conversation.py`
- `swarmmind/models.py`
- `swarmmind/api/supervisor.py`
- `ui/src/App.tsx`
- `docs/ui/30-projects-and-project-space.md`

### 验收标准

- 用户能从一次有效对话提升出一个真实 Project 入口
- 提升后不是复制 thread, 而是形成结构化摘要
- 项目页至少能展示“从哪来、要做什么、下一步是什么”

### 预估

- 人类团队: 4-5 天
- CC + gstack: 0.5-1 天

---

## M4. 精选多模型支持

### 目标

在不引入平台复杂度的前提下, 把已有 runtime catalog 变成用户可感知的能力选择。

### 交付内容

- 支持多个模型被分配给同一 subject
- 模型选择器展示能力语义而不是 provider 术语
- 默认模型、推荐模型、受限模型规则清晰
- 后端校验“可选模型集合”, 前端只消费可用列表

### 明确不做

- 用户自助填 API key
- 全量 provider CRUD 页面
- 企业级模型权限系统

### 建议落点

- `swarmmind/runtime/catalog.py`
- `swarmmind/repositories/runtime_catalog.py`
- `swarmmind/runtime/profile.py`
- `ui/src/components/ui/v0-ai-chat.tsx`

### 验收标准

- 至少 2-3 个模型可以稳定出现在 picker 中
- 切换模型后会话请求真正使用新模型
- 不可用模型请求会被后端明确拒绝
- 前端不需要知道 provider 细节也能完成选择

### 预估

- 人类团队: 3-4 天
- CC + gstack: 0.5 天

---

## 8. 用户系统启动条件

只有在以下三项同时成立时, 用户系统才进入下一阶段主计划:

1. `Promote to Project` 已落地
2. Project 页面已承接真实对象而非占位
3. 明确出现“一个项目需要多人访问或权限隔离”的真实场景

启动后第一阶段只做:

- 登录态
- 会话归属
- 最小用户历史

不直接进入:

- 组织架构
- 完整 RBAC
- 审批流权限矩阵

---

## 9. 风险与约束

### 风险 1: 继续横向铺页面

风险:

占位页越来越多, 但主路径仍不够强, 最终产品给人的感受会是“什么都有一点, 但没有一条能走到底”。

应对:

本计划期间不扩展 Teams / Skills / Knowledge / Schedules 的实装范围。

### 风险 2: DeerFlow 集成变成平台工程

风险:

陷入底层抽象、术语暴露和事件复杂度, 消耗主路径时间。

应对:

只接受能直接改善 ChatSession 体验的 DeerFlow 集成项。

### 风险 3: 多模型支持过早平台化

风险:

被 provider 配置、密钥管理、兼容层吸走精力。

应对:

只做“已分配模型列表 + 默认模型 + 切换校验”。

### 风险 4: 技术债继续累积

风险:

测试虽然全绿, 但数据库连接和时间 API 警告已经在提醒底座粗糙度。

应对:

在执行 M1-M2 时顺手清掉以下底层项:

- SQLite 连接未关闭警告
- `datetime.utcnow()` 迁移到 timezone-aware UTC
- FastAPI startup 迁移到 lifespan

---

## 10. 执行顺序建议

推荐顺序:

1. M1 `ChatSession 主路径闭环`
2. M2 `DeerFlow 最小深集成`
3. M3 `最小 Promote to Project`
4. M4 `精选多模型支持`
5. 用户系统单独立项

注意:

- M2 可以与 M1 后半段交叉推进
- M3 必须在 M1 稳定后开始
- M4 必须等主路径稳定后再产品化
- 用户系统不能插队

---

## 11. 成功标准

当以下条件成立时, 这轮计划算成功:

- 新用户能在 10 分钟内完成一次完整 ChatSession
- 高价值对话可以自然提升为 Project
- `pro / ultra` 模式带来的差异用户可明显感知
- 多模型选择不再是“技术配置”, 而是“任务策略选择”
- 团队可以明确回答“为什么现在不先做用户系统”

---

## 12. 后续文档动作

本计划执行过程中:

- 若范围变化, 直接更新本文档
- 若某个子模块范围扩大到独立工作流, 再拆出专项计划
- 本计划完成后, 归档到 `docs/archive/`

