# SwarmMind Chat UI 移植执行计划

> **文档类型**: [B] 工程状态文档 — 一次性执行计划  
> **状态**: 执行中，完成后归档  
> 目标：从 DeerFlow 移植 Chat UI 组件到 SwarmMind
> 预计工期：5 个工作日
> 执行方式：直接复制可用组件 + 重写核心逻辑

---

## 第一阶段：环境准备（第 1 天上午）

### 1.1 创建组件目录结构

```bash
# 在 SwarmMind 项目根目录执行
mkdir -p ui/src/components/ai-elements
mkdir -p ui/src/components/workspace/messages
mkdir -p ui/src/components/workspace/artifacts
mkdir -p ui/src/components/workspace/tasks
mkdir -p ui/src/core/messages
mkdir -p ui/src/core/tasks
mkdir -p ui/src/core/artifacts
mkdir -p ui/src/core/i18n
mkdir -p ui/src/core/utils
```

### 1.2 安装依赖检查

```bash
# 检查 DeerFlow 使用的额外依赖
cd /Users/krli/workspace/SwarmMindProject/deer-flow/frontend && cat package.json | grep -E '"streamdown"|"rehype-katex"|"remark-gfm"|"@radix-ui/react-use-controllable-state"'

# 在 SwarmMind 中安装缺失依赖
cd /Users/krli/workspace/SwarmMindProject/SwarmMind/ui
pnpm add rehype-katex remark-gfm  # 如果尚未安装
```

---

## 第二阶段：基础组件移植（第 1 天下午 - 第 2 天）

### 2.1 可直接复制的 UI 组件（纯展示型）

以下组件**无需修改**或**仅需修改导入路径**即可使用：

```bash
# 复制 Shimmer 组件
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/shimmer.tsx \
   ui/src/components/ai-elements/shimmer.tsx

# 复制 Sources 组件
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/sources.tsx \
   ui/src/components/ai-elements/sources.tsx

# 复制 Checkpoint 组件
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/checkpoint.tsx \
   ui/src/components/ai-elements/checkpoint.tsx

# 复制 Toolbar 组件
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/toolbar.tsx \
   ui/src/components/ai-elements/toolbar.tsx
```

### 2.2 需要适配导入路径的组件

复制后执行字符串替换：

```bash
# 函数：修复导入路径
fix_imports() {
    local file=$1
    # 替换 DeerFlow 路径为 SwarmMind 路径
    sed -i '' 's|@/components/ui/|@/components/ui/|g' "$file"
    sed -i '' 's|@/lib/utils|@/lib/utils|g' "$file"
    # 删除 DeerFlow 特有的导入（后续手动处理）
}

# 应用修复
fix_imports ui/src/components/ai-elements/shimmer.tsx
fix_imports ui/src/components/ai-elements/sources.tsx
fix_imports ui/src/components/ai-elements/checkpoint.tsx
```

---

## 第三阶段：核心组件重写（第 2-4 天）

### 3.1 Reasoning 组件（抄 DeerFlow 功能）

**参考源：** `deer-flow/frontend/src/components/ai-elements/reasoning.tsx`

**重写目标文件：** `ui/src/components/ai-elements/reasoning.tsx`

**核心差异：**
- DeerFlow 使用 `streamdown` + `additional_kwargs.reasoning_content`
- SwarmMind 已有 `Streamdown`，复用即可

```typescript
// 重写要点 - 参考 DeerFlow 但适配 SwarmMind 数据结构：
// 1. 保留 duration 计算逻辑
// 2. 保留 auto-close 逻辑  
// 3. 保留 Shimmer 动画
// 4. 适配 SwarmMind 的 thinking 数据流
```

**执行命令：**
```bash
# 先复制作为基础，然后重写
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/reasoning.tsx \
   ui/src/components/ai-elements/reasoning-new.tsx

# 然后参考本文档的"重写指南"手动修改
# 修改完成后替换原文件
mv ui/src/components/ai-elements/reasoning-new.tsx \
   ui/src/components/ai-elements/reasoning.tsx
```

### 3.2 Task 组件（简化版）

**参考源：** `deer-flow/frontend/src/components/ai-elements/task.tsx`

**执行：**
```bash
# 直接复制，几乎无需修改
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/task.tsx \
   ui/src/components/ai-elements/task.tsx
```

### 3.3 Artifact 基础组件

**参考源：** `deer-flow/frontend/src/components/ai-elements/artifact.tsx`

**执行：**
```bash
# 复制基础组件
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/artifact.tsx \
   ui/src/components/ai-elements/artifact.tsx
```

---

## 第四阶段：核心功能开发（第 3-5 天）

### 4.1 ChainOfThought 组件（必须重写）

**目标文件：** `ui/src/components/ai-elements/chain-of-thought.tsx`

**参考 DeerFlow：** `deer-flow/frontend/src/components/ai-elements/chain-of-thought.tsx`

**核心功能抄过来：**
- Collapsible 结构
- Step 展示逻辑
- 图标映射（SearchIcon, GlobeIcon 等）

**数据流适配：**
```typescript
// DeerFlow 数据结构：
interface Message {
  type: 'ai' | 'tool';
  tool_calls?: Array<{name: string, args: any}>;
}

// SwarmMind 数据结构：
interface StreamEvent {
  type: 'team_task' | 'team_activity';
  task?: RuntimeTask;
  activity?: RuntimeActivity;
}
```

### 4.2 SubtaskCard 组件（高优先级）

**目标文件：** `ui/src/components/workspace/messages/subtask-card.tsx`

**从 DeerFlow 抄写：**
```bash
# 复制基础结构
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/workspace/messages/subtask-card.tsx \
   ui/src/components/workspace/messages/subtask-card.tsx
```

**需要修改的部分：**
1. 删除 `useSubtask()` hook 调用，改为 props 传递
2. 删除 `useI18n()`，改为硬编码或 props
3. 保留视觉结构：ChainOfThought + ShineBorder + 状态图标
4. 保留动画：Shimmer duration={3} spread={3}

### 4.3 PromptInput 组件（文件上传核心）

**目标文件：** `ui/src/components/ai-elements/prompt-input.tsx`

**抄写策略：**
```bash
# 复制完整文件
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/prompt-input.tsx \
   ui/src/components/ai-elements/prompt-input.tsx
```

**关键修改点：**
1. 删除 `usePromptInputController` provider 逻辑，改为本地 state
2. 简化 `PromptInputProvider`，与 SwarmMind 的 v0-ai-chat 集成
3. 保留核心功能：
   - 拖放上传
   - 粘贴上传
   - 附件预览
   - Backspace 删除附件

**需要创建的类型文件：**
```typescript
// ui/src/core/messages/types.ts
export interface FileUIPart {
  type: 'file';
  url: string;
  mediaType: string;
  filename: string;
}
```

---

## 第五阶段：工具函数和工具类（第 4-5 天）

### 5.1 复制工具函数

```bash
# 文件工具
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/core/utils/files.tsx \
   ui/src/core/utils/files.tsx

# UUID 工具（如不存在）
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/core/utils/uuid.ts \
   ui/src/core/utils/uuid.ts

# 日期时间工具（可选）
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/core/utils/datetime.ts \
   ui/src/core/utils/datetime.ts
```

### 5.2 消息处理工具（重写）

**参考源：** `deer-flow/frontend/src/core/messages/utils.ts`

**创建文件：** `ui/src/core/messages/utils.ts`

**抄写以下函数：**
- `extractContentFromMessage()` - 提取消息内容
- `extractReasoningContentFromMessage()` - 提取 reasoning
- `hasContent()` - 判断是否有内容
- `hasReasoning()` - 判断是否有 reasoning
- `groupMessages()` - 消息分组逻辑

**适配 SwarmMind 数据：**
```typescript
// SwarmMind ChatMessage 结构
interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  thinking?: string;
  isStreaming?: boolean;
  isReasoningStreaming?: boolean;
}
```

---

## 第六阶段：v0-ai-chat.tsx 重构（第 5 天）

### 6.1 渐进式重构策略

不一次性重写，而是逐步替换：

**步骤 1：替换 ReasoningPanel**
```typescript
// 删除原有的 ReasoningPanel 组件定义
// 导入新的组件
import { Reasoning, ReasoningTrigger, ReasoningContent } from '@/components/ai-elements/reasoning';
```

**步骤 2：添加文件上传支持**
```typescript
// 在 MessageBubble 组件中添加文件展示
// 使用 PromptInputAttachment 组件
```

**步骤 3：添加子任务展示**
```typescript
// 在 handleStreamEvent 中处理 team_task 事件
// 渲染 SubtaskCard 组件
```

---

## 具体文件映射表

| DeerFlow 源文件 | SwarmMind 目标文件 | 操作 | 工作量 |
|----------------|-------------------|------|--------|
| `ai-elements/shimmer.tsx` | `ai-elements/shimmer.tsx` | **直接复制** | 5分钟 |
| `ai-elements/sources.tsx` | `ai-elements/sources.tsx` | **直接复制** | 5分钟 |
| `ai-elements/checkpoint.tsx` | `ai-elements/checkpoint.tsx` | **直接复制** | 5分钟 |
| `ai-elements/task.tsx` | `ai-elements/task.tsx` | **直接复制** | 5分钟 |
| `ai-elements/artifact.tsx` | `ai-elements/artifact.tsx` | **直接复制** | 5分钟 |
| `ai-elements/toolbar.tsx` | `ai-elements/toolbar.tsx` | **直接复制** | 5分钟 |
| `ai-elements/reasoning.tsx` | `ai-elements/reasoning.tsx` | **抄写修改** | 2小时 |
| `ai-elements/chain-of-thought.tsx` | `ai-elements/chain-of-thought.tsx` | **抄写重写** | 3小时 |
| `ai-elements/prompt-input.tsx` | `ai-elements/prompt-input.tsx` | **抄写修改** | 4小时 |
| `workspace/messages/subtask-card.tsx` | `workspace/messages/subtask-card.tsx` | **抄写修改** | 2小时 |
| `workspace/streaming-indicator.tsx` | `workspace/streaming-indicator.tsx` | **直接复制** | 5分钟 |
| `core/utils/files.tsx` | `core/utils/files.tsx` | **直接复制** | 5分钟 |
| `core/messages/utils.ts` | `core/messages/utils.ts` | **抄写重写** | 2小时 |

---

## 重写指南（抄功能要点）

### Reasoning 组件重写要点

```typescript
// 从 DeerFlow 抄写以下功能：

// 1. 状态管理
const [isOpen, setIsOpen] = useControllableState({ defaultProp: defaultOpen });
const [duration, setDuration] = useControllableState({ prop: durationProp });
const [hasAutoClosed, setHasAutoClosed] = useState(false);
const [startTime, setStartTime] = useState<number | null>(null);

// 2. 时长跟踪
useEffect(() => {
  if (isStreaming) {
    if (startTime === null) setStartTime(Date.now());
  } else if (startTime !== null) {
    setDuration(Math.ceil((Date.now() - startTime) / 1000));
    setStartTime(null);
  }
}, [isStreaming, startTime]);

// 3. 自动关闭
useEffect(() => {
  if (defaultOpen && !isStreaming && isOpen && !hasAutoClosed) {
    const timer = setTimeout(() => {
      setIsOpen(false);
      setHasAutoClosed(true);
    }, 1000);
    return () => clearTimeout(timer);
  }
}, [isStreaming, isOpen, defaultOpen, hasAutoClosed]);

// 4. 文案逻辑
const getThinkingMessage = (isStreaming: boolean, duration?: number) => {
  if (isStreaming || duration === 0) {
    return <Shimmer duration={1}>思考中...</Shimmer>;
  }
  if (duration === undefined) return "思考了几秒";
  return `思考完成，用时 ${duration} 秒`;
};
```

### ChainOfThought 组件重写要点

```typescript
// 核心结构抄 DeerFlow：
<ChainOfThought>
  <ChainOfThoughtStep 
    label={toolCallDescription}
    icon={getIconForTool(toolName)}
  >
    {toolResult && <ChainOfThoughtSearchResult>{result}</ChainOfThoughtSearchResult>}
  </ChainOfThoughtStep>
</ChainOfThought>

// 工具图标映射抄过来：
const TOOL_ICONS: Record<string, LucideIcon> = {
  web_search: SearchIcon,
  web_fetch: GlobeIcon,
  read_file: BookOpenTextIcon,
  write_file: NotebookPenIcon,
  bash: SquareTerminalIcon,
  // ...
};
```

### PromptInput 重写要点

```typescript
// 核心 hooks 抄写：
const [files, setFiles] = useState<File[]>([]);
const fileInputRef = useRef<HTMLInputElement>(null);

// 拖放处理抄过来：
const onDragOver = (e: DragEvent) => {
  if (e.dataTransfer?.types?.includes("Files")) {
    e.preventDefault();
  }
};

const onDrop = (e: DragEvent) => {
  e.preventDefault();
  if (e.dataTransfer?.files) {
    addFiles(e.dataTransfer.files);
  }
};

// 粘贴处理抄过来：
const handlePaste = (e: ClipboardEvent) => {
  const items = e.clipboardData?.items;
  if (!items) return;
  
  const files: File[] = [];
  for (const item of items) {
    if (item.kind === "file") {
      const file = item.getAsFile();
      if (file) files.push(file);
    }
  }
  
  if (files.length > 0) {
    e.preventDefault();
    addFiles(files);
  }
};
```

---

## 执行检查清单

### 第 1 天
- [ ] 目录结构创建
- [ ] shimmer.tsx 复制并验证
- [ ] sources.tsx 复制并验证
- [ ] checkpoint.tsx 复制并验证
- [ ] task.tsx 复制并验证

### 第 2 天
- [ ] reasoning.tsx 重写完成
- [ ] artifact.tsx 复制并验证
- [ ] chain-of-thought.tsx 结构搭建
- [ ] files.tsx 工具函数复制

### 第 3 天
- [ ] chain-of-thought.tsx 完成
- [ ] subtask-card.tsx 完成
- [ ] prompt-input.tsx 基础结构

### 第 4 天
- [ ] prompt-input.tsx 文件上传完成
- [ ] messages/utils.ts 工具函数
- [ ] 类型定义文件创建

### 第 5 天
- [ ] v0-ai-chat.tsx 集成新组件
- [ ] ReasoningPanel 替换
- [ ] 功能测试
- [ ] Bug 修复

---

## 快速开始命令

```bash
# 1. 进入项目目录
cd /Users/krli/workspace/SwarmMindProject/SwarmMind

# 2. 创建所有目录
mkdir -p ui/src/components/{ai-elements,workspace/{messages,artifacts,tasks}}
mkdir -p ui/src/core/{messages,tasks,artifacts,i18n,utils}

# 3. 复制所有可直接使用的组件
for file in shimmer sources checkpoint task artifact toolbar; do
  cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/ai-elements/$file.tsx \
     ui/src/components/ai-elements/$file.tsx
done

# 4. 复制工具函数
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/core/utils/files.tsx \
   ui/src/core/utils/files.tsx

# 5. 复制流式指示器
cp /Users/krli/workspace/SwarmMindProject/deer-flow/frontend/src/components/workspace/streaming-indicator.tsx \
   ui/src/components/workspace/streaming-indicator.tsx 2>/dev/null || echo "文件不存在，手动创建"

echo "基础组件复制完成！开始重写核心组件..."
```

---

## 注意事项

1. **路径问题**：SwarmMind 使用 `@/` 别名，DeerFlow 也是 `@/`，无需修改
2. **UI 组件库**：两者都使用 shadcn/ui，组件 API 一致
3. **样式类名**：DeerFlow 使用 Tailwind，SwarmMind 也是，大部分无需修改
4. **Streamdown**：两者都使用，渲染逻辑一致
5. **依赖检查**：确保 `rehype-katex` 和 `remark-gfm` 已安装

---

*计划完成 - 开始执行*
