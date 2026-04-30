# SwarmMind

> 开源的 **企业 Agent 控制平面**。
> 把分散的企业内部系统转换为可治理、可审计、可执行的组织上下文。

[English](README.md)

## 为什么是 SwarmMind

大量“多 Agent”项目停留在演示层，企业落地卡在最后一公里：

- 数据分散在 OA / CRM / 财务 / HR / 代码系统；
- 权限体系复杂，风险高；
- 执行动作需要审批、可回滚；
- 管理者需要可追溯证据，而不是静态周报。

SwarmMind 解决的是这个企业级操作层，而不只是“让 Agent 聊天协作”。

## 产品定位

SwarmMind **不是**又一个多 Agent 框架。

它是一个企业 Agent 控制平面，提供：

- **可治理上下文层（Governed Context Layer）**：来源追踪、权限范围、置信度、版本、TTL、冲突集；
- **自适应路由与策略学习（Adaptive Routing & Policy Learning）**：可观察、可回滚；
- **执行轨迹（Execution Trace）**：步骤、工具调用、证据链接、审批状态全程可审计；
- **上下文到视图编译器（Context-to-View Compiler）**：将上下文编译为结构化视图（状态、时间线、风险、决策日志）。

## 核心理念

1. **Agent 是主要执行者，人类是监督者与裁决者。**
2. **状态是上下文，而不是工单字段。**
3. **治理优先**：权限边界与审计能力是第一优先级。
4. **企业级可靠性优先于 Demo 式自治。**

## 文档导航

- [文档首页](docs/README.md)
- [产品定位](docs/product-positioning.md)
- [技术架构](docs/architecture.md)
- [路线图](docs/roadmap.md)
- [ChatSession 主路径计划](docs/chat-mainline-execution-plan.md)
- [历史版本叙事归档](docs/archive/README_v1_vision.md)

## 当前研发重点

- P0：保持 ChatSession 可靠，并闭环 `Promote to Project`
- P1：让 Project 承接 run、artifact、审批和审计，形成可治理执行边界
- P2：在主路径成立后，再扩展企业连接器和策略智能

## 快速开始

```bash
make install
make dev
```

## 许可证

[GNU Affero 通用公共许可证 v3.0](LICENSE) (AGPL-3.0)
