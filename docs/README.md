# SwarmMind 文档总览

> 日期：2026-04-08
> 用途：定义当前文档体系的主入口，区分前瞻性设计与工程实现状态

## 0. 文档分类体系

本文档体系采用两级分类：

### [A] 前瞻性架构文档 (Target Architecture)

描述**目标状态、设计决策、长期演进方向**的文档。它们是代码的"应然"状态。

- `docs/architecture.md` — 唯一主架构基线
- `DESIGN.md` — 设计系统规范
- `docs/ui/*.md` — UI 线框与交互规则
- `docs/enterprise-crm-user-story.md` — 场景验证文档

**阅读场景**: 做架构设计、技术决策、理解长期演进方向

### [B] 工程状态文档 (Implementation Status)

描述**当前代码已实现**的工程状态、接口定义、部署配置的文档。它们是代码的"实然"状态。

- `AGENTS.md` — 当前工程状态总览（含 Phase A 实现清单）
- `docs/README.md` — 本文档，文档体系元数据
- `docs/archive/*` — 已完成的临时调研与执行文档（如 gap-analysis、migration-plan）

**阅读场景**: 理解当前代码能做什么、如何运行、如何部署

### 使用指南

| 你的目标 | 优先阅读 |
|---------|---------|
| 理解 SwarmMind 应该是什么（架构愿景） | [A] `docs/architecture.md` |
| 理解 SwarmMind 当前实现了什么 | [B] `AGENTS.md` |
| 实现新功能 | [A] 确定目标 + [B] 确定起点 |
| 运行或部署系统 | [B] `AGENTS.md` §Running |

---

## 1. 规范

- `docs/architecture.md` 是唯一主架构基线。
- UI 线框只保留在 `docs/ui/` 目录。
- 用户故事文档用于场景校验，不得反向覆盖主架构。
- **实现计划、调研草稿**（如 `chat-ui-gap-analysis.md`, `ui-migration-plan.md`）属于临时文档，执行完成后应删除或归档。

## 2. 当前文档层次

### A. 主架构 [A]

- `docs/architecture.md`

用途：

- 定义术语表
- 定义控制面 / 执行面边界
- 定义 DeerFlow Runtime、RuntimeProfile、RuntimeInstance、Runtime Container
- 定义实施路线和非目标

### B. UI 线框

- `DESIGN.md`
- `docs/ui/README.md`
- `docs/ui/01-navigation-and-principles.md`
- `docs/ui/02-page-map-and-flows.md`
- `docs/ui/10-workbench-and-chat.md`
- `docs/ui/20-skill-center.md`
- `docs/ui/30-projects-and-project-space.md`
- `docs/ui/40-approval-center.md`
- `docs/ui/60-knowledge-library-schedules.md`

用途：

- `DESIGN.md` 承接视觉系统、设计 token 和跨页面设计边界
- `docs/ui/*` 承接主架构到页面骨架
- `docs/ui/*` 定义导航、布局、页面状态和交互规则

### C. 场景验证

- `docs/enterprise-crm-user-story.md`

用途：

- 保留一份规范场景文档，用端到端故事验证主架构和 UI 是否闭环
- 其他业务域的稳定结论优先并入 `docs/architecture.md`
- 不长期维护多份并行用户故事，避免再次引入旧术语和第二套对象模型

当前说明：

- 原 `marketing-campaign`、`hr-recruiting` 场景稿已删除。
- 它们留下的有效结论已收敛到 `docs/architecture.md` 的“跨业务场景边界”。
- 当前只保留 `enterprise-crm` 作为规范场景样本。

## 3. 清理规则

- 新增文档前，先判断能否写入现有正式文档（参考上方 [A]/[B] 分类）。
- **[A] 类文档**（架构、设计规范）变更需经过架构决策流程。
- **[B] 类文档**（工程状态）随代码迭代更新，保持与实现同步。
- **临时调研文档**（如 gap-analysis、migration-plan）一旦执行完成，应删除或归档到 `docs/archive/`，不长期保留。
- 引用链必须指向当前正式文档，不应继续引用已删除的母稿或过渡稿。
- 研究类文档若已经偏离当前主路线，且未进入正式架构承诺，应删除而不是长期悬挂。

## 4. 文档维护责任

| 文档 | 类型 | 维护责任 | 更新触发条件 |
|------|------|---------|-------------|
| `architecture.md` | [A] | 架构师 | 架构决策、Phase 演进 |
| `DESIGN.md` | [A] | 设计负责人 | 设计系统变更 |
| `docs/ui/*.md` | [A] | 前端负责人 | 新页面/流程设计 |
| `AGENTS.md` | [B] | 全团队 | 每次迭代完成后 |
| `docs/README.md` | [B] | 架构师 | 文档体系结构调整 |
