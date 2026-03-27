# SwarmMind UI 线框文档

> 日期：2026-03-27
> 用途：基于现有架构文档，产出 Supervisor UI 的完整页面线框集合
> 主要依据：`docs/frontend-ui-spec.md`、`docs/architecture.md`、`docs/enterprise-crm-user-story.md`、`docs/team-interface-agent-adr.md`、`docs/workflow-template-system.md`、`docs/mcp-skill-integration.md`

## 1. 文档目标

这套文档不是视觉稿，而是面向产品、设计和前端实现的结构化线框说明。

目标有三点：

- 把架构文档里的抽象对象转成真实可用页面
- 明确 Supervisor UI 不是普通聊天界面，而是 AI Team 控制面
- 为后续视觉设计、交互稿和前端实现提供统一骨架

## 2. 阅读顺序

1. `01-navigation-and-principles.md`
2. `02-page-map-and-flows.md`
3. `10-workbench-and-chat.md`
4. `20-skill-center.md`
5. `30-projects-and-project-space.md`
6. `40-approval-center.md`
7. `60-knowledge-library-schedules.md`

## 3. 页面清单

本目录覆盖的页面如下：

- 工作台
- 新建对话 / 轻量 ChatSession
- 最近记录
- 技能中心
- 项目列表
- 新建项目
- 项目总览
- 项目协作台
- 项目看板
- 项目时间线与风险
- 项目产物库
- 项目设置 / Team 挂载
- 审批中心
- 资源库
- 知识库
- 定时任务
- 设置

## 4. 页面方法

除基础规则文档外，每个页面都遵循同一描述结构：

- 页面卡片
- 信息结构
- 桌面端线框
- 关键交互
- 状态设计
- 移动端规则

## 5. 设计结论

SwarmMind 的 UI 核心不是“多几个 tab 的聊天壳”，而是三层清晰控制面：

- 会话层：让用户快速探索与发起
- 项目层：承接正式协作、Team、任务、产物和审批
- 治理层：承接技能治理、审批治理和权限化工作台聚合
