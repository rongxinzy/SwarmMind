# Contributing to SwarmMind

感谢您对 SwarmMind 项目的关注！本文档描述了如何为项目做出贡献。

## 分支保护规则

本项目采用严格的分支保护策略，确保代码质量和协作规范。

### 受保护的分支

| 分支 | 保护级别 | 说明 |
|------|----------|------|
| `main` | 🔒 严格保护 | 必须通过 PR + 至少 1 人审查 |
| `release*` | 🔒 严格保护 | 必须通过 PR + 至少 1 人审查 |

### 例外情况

| 用户 | 权限 | 说明 |
|------|------|------|
| `hawkli-1994` (Owner) | ✅ 可绕过审查 | 允许自审查和合并自己的 PR |

> **说明**：当前项目处于早期开发阶段，仅有单一维护者。为了不影响开发效率，仓库所有者可以绕过审查要求直接合并自己的 PR。当项目有多个贡献者时，此例外将被移除。

### 禁止的操作

以下操作在受保护分支上将被 **拒绝**（Owner 除外）：

- ❌ 直接推送 (`git push origin main`)
- ❌ 强制推送 (`git push --force`)
- ❌ 删除分支 (`git push origin --delete main`)

## 分支命名规范

所有开发工作必须在独立的功能分支上进行，禁止直接向受保护分支推送。

### 分支命名格式

```
<type>/<short-description>
```

### 分支类型 (Type)

| 类型 | 用途 | 示例 |
|------|------|------|
| `feature` | 新功能开发 | `feature/user-auth` |
| `fix` | Bug 修复 | `fix/memory-leak` |
| `docs` | 文档更新 | `docs/api-guide` |
| `refactor` | 代码重构（不改变功能） | `refactor/dispatch-logic` |
| `test` | 测试相关 | `test/shared-memory` |
| `chore` | 构建/工具/配置变更 | `chore/update-deps` |
| `perf` | 性能优化 | `perf/query-cache` |
| `release` | 版本发布准备 | `release/v1.0.0` |

### 命名规则

1. **使用小写字母**：全部小写，避免大小写混淆
2. **使用连字符分隔单词**：`feature/user-auth` ✅ `feature/userAuth` ❌
3. **简短描述**：描述应简洁明了，2-4 个词为宜
4. **关联 Issue**：如有对应 Issue，可在描述中包含编号
   - 示例：`fix/#123-memory-leak`

### 完整示例

```bash
# ✅ 正确的分支命名
git checkout -b feature/context-broker-routing
git checkout -b fix/#456-null-pointer
git checkout -b docs/contributing-guide
git checkout -b refactor/simplify-memory-layer
git checkout -b test/layered-memory-edge-cases
git checkout -b chore/update-readme-badges
git checkout -b perf/reduce-db-queries

# ❌ 错误的分支命名
git checkout -b Feature/NewThing      # 大写字母
git checkout -b fix_memory_leak       # 使用下划线
git checkout -b my-branch             # 缺少类型前缀
git checkout -b feature/fix/docs      # 多个类型
git checkout -b fix                   # 缺少描述
```

### 长生命周期分支

以下分支具有特殊含义，请勿随意创建：

| 分支 | 用途 | 保护状态 |
|------|------|----------|
| `main` | 主分支，稳定代码 | 🔒 严格保护 |
| `release/*` | 版本发布分支 | 🔒 严格保护 |
| `hotfix/*` | 紧急修复（从 release 分支创建） | 遵循功能分支规范 |

## 开发工作流程

### 1. 创建功能分支

```bash
# 确保本地 main 是最新的
git checkout main
git pull origin main

# 创建功能分支（遵循上述命名规范）
git checkout -b <type>/<short-description>

# 示例
git checkout -b feature/context-broker-routing
```

### 2. 开发与提交

```bash
# 进行代码修改
# ...

# 提交更改（遵循 Conventional Commits 规范）
git add .
git commit -m "feat: add new feature description"

# 推送到远程
git push origin feature/your-feature-name
```

**Commit 规范示例：**

- `feat: add user authentication`
- `fix: resolve memory leak in context broker`
- `docs: update API documentation`
- `refactor: simplify dispatch logic`
- `test: add unit tests for shared memory`

### 3. 创建 Pull Request

```bash
# 使用 GitHub CLI 创建 PR
gh pr create --title "feat: your feature title" --body "PR description"

# 或在 GitHub Web 界面操作
```

**PR 要求：**

- [ ] 标题清晰描述变更内容
- [ ] 描述中包含变更动机和实现细节
- [ ] 所有 CI 检查通过
- [ ] 获得至少 **1 人** 审查批准
- [ ] 解决所有审查意见

### 4. 代码审查

PR 创建后，需要等待审查。

- 审查者会检查代码质量、架构合理性和测试覆盖
- 如有修改意见，请继续提交到同一分支
- 所有对话解决后，审查者会批准 PR

### 5. 合并 PR

获得批准后，可以使用以下方式合并：

```bash
# 确保 PR 是最新的（rebase 到最新 main）
git checkout feature/your-feature-name
git fetch origin
git rebase origin/main
git push origin feature/your-feature-name --force-with-lease

# 在 GitHub 上点击 "Merge pull request"
# 或使用 GitHub CLI
gh pr merge --squash --delete-branch
```

**合并方式：**

- 推荐使用 **Squash and merge** 保持 main 分支历史整洁
- 合并后会自动删除功能分支

## 代码规范

### Python

- 4 空格缩进
- 类型提示（Type Hints）
- 遵循 PEP 8
- 使用 Ruff 进行代码检查（`make typecheck`）

### TypeScript / React

- PascalCase 组件名
- camelCase 变量和函数
- 分组导入语句
- shadcn/ui 风格组件

### 测试

```bash
# 运行后端测试
make test

# 确保新功能有对应的测试覆盖
```

## 报告 Bug

如果您发现了 Bug，请：

1. 先搜索现有 Issues，避免重复提交
2. 创建新 Issue，包含：
   - 问题描述
   - 复现步骤
   - 期望行为 vs 实际行为
   - 环境信息（OS、Python 版本等）
   - 相关日志或截图

## 功能建议

欢迎提出新功能建议！请：

1. 先查看 Roadmap 和现有 Issues
2. 创建 Feature Request Issue，描述：
   - 功能动机
   - 预期行为
   - 可能的实现方案
   - 是否愿意实现（可选）

## 开发环境设置

```bash
# 1. 克隆仓库
git clone https://github.com/rongxinzy/SwarmMind.git
cd SwarmMind

# 2. 安装依赖
make install

# 3. 复制环境变量配置
cp .env.example .env
# 编辑 .env 填入必要的 API Keys

# 4. 启动开发服务器
make dev
```

## 获取帮助

如有疑问，可以通过以下方式联系：

- GitHub Discussions
- GitHub Issues
- 项目文档：`docs/` 目录

---

再次感谢您对 SwarmMind 的贡献！🚀
