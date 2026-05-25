# Phase166 Longform Batch Chat Projection Report

## Scope

本阶段将 `inspect_longform_chapter_batch` 接入前端 Agent run action descriptor registry。目标是让长篇批次队列检查结果在 Hermes 聊天中显示为稳定中文摘要，而不是裸露 `inspect_longform_chapter_batch` 工具名。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - 新增 `inspect_longform_chapter_batch` action descriptor。
  - 新增 fallback label:
    - `长篇批次检查已生成`
    - `长篇批次未找到`
    - `长篇批次检查失败`
    - `长篇批次检查中`
  - 从后端既有字段提取安全摘要：
    - 队列深度
    - 活跃任务
    - 命中任务
    - 章节范围
    - 执行状态
  - 避免渲染 plan hash 等内部字段。
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - 覆盖 descriptor 识别、run id 提取、完成态 fallback 和 not-found fallback。
- `frontend/src/components/chat/ChatMessage.test.ts`
  - 覆盖缺少后端 `action_result_view` 时的聊天渲染 fallback。

## Validation

### RED

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Expected failure observed:

- `inspect_longform_chapter_batch` 未被识别。
- Descriptor lookup 返回空。
- 聊天渲染回退为原始工具名。

### GREEN

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Result:

- 2 test files passed.
- 30 tests passed.

### T1 Regression

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 35 tests passed.

Command:

```powershell
cd frontend
npm run build
```

Result:

- `vue-tsc --noEmit` passed.
- `vite build` passed.

### Hygiene

Command:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

- `git diff --check`: no output.
- Secret scan: no matches.

## Next Recommendation

继续沿 descriptor registry 扩展下一类高价值 Agent 工具投影。优先级建议：

1. `execute_longform_chapter_batch_preflight`
2. `prepare_longform_chapter_batch_execution`
3. `execute_longform_chapter_batch`

原因：这三个工具是长篇批次从“队列检查”走向“可恢复、可审批、可执行”的核心链路。聊天投影补齐后，用户能在对话内判断当前批次是否可执行、为什么阻塞，以及下一步需要调用哪个 Agent 工具。
