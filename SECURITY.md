# 安全策略 / Security Policy

## 受支持版本 / Supported Versions

SwarmMind 目前处于早期开发阶段（pre-1.0），仅维护 `main` 分支。我们不为已发布的旧版本提供安全补丁；请始终使用 `main` 分支或最新 release。

| 版本 / Version | 是否维护 / Supported |
|----------------|---------------------|
| `main` (latest) | ✅ |
| `< 0.x`         | ❌ |

## 报告安全漏洞 / Reporting a Vulnerability

**请不要通过公开 issue、Pull Request 或 Discussions 报告安全问题。**
**Please do NOT report security issues through public GitHub issues, PRs, or discussions.**

请通过以下任一私密渠道联系：

1. **GitHub Security Advisory（首选）** —
   <https://github.com/rongxinzy/SwarmMind/security/advisories/new>
   该渠道支持私密讨论、CVE 申请与协调披露。

2. **邮件** — 暂未公开。如需邮件渠道，请先在 Security Advisory 中说明，我们会私下发送联系方式。

报告时请尽量包含：

- 漏洞类型（如 RCE、SSRF、越权、依赖链问题等）
- 受影响的文件 / 路径 / 接口
- 复现步骤或 PoC
- 你认为的影响范围与严重等级
- （可选）建议的修复方向

## 响应时效 / Response SLA

| 阶段 | 目标时间 |
|------|---------|
| 收到报告后首次确认 | 3 个工作日内 |
| 初步评估与严重度分级 | 7 个工作日内 |
| 修复发布（视严重度） | 高危 ≤ 30 天，中低危 ≤ 90 天 |

## 协调披露 / Coordinated Disclosure

我们采用协调披露原则：

- 在补丁发布前，请勿公开漏洞细节。
- 修复发布后，我们会在 release notes 与 advisory 中致谢报告者（除非你要求匿名）。
- 如发现 90 天后仍未修复，欢迎与我们再次确认进度。

## 范围 / Scope

**在范围内**：
- `swarmmind/` 后端代码
- `ui/` 前端代码
- `alembic/` 数据库迁移脚本
- `.github/workflows/` CI 配置
- 默认部署方式（`make dev` / Docker 镜像，如有）

**不在范围内**：
- 第三方依赖的已知漏洞（请直接向上游报告，但欢迎提醒我们升级）
- 用户自行修改后的部署
- 社会工程学、物理攻击、DoS

## 致谢 / Acknowledgements

感谢所有负责任地报告漏洞、帮助 SwarmMind 变得更安全的研究者。
