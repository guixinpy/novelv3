# Phase169 Longform Execute Chat Projection Report

## Scope

本阶段将 `execute_longform_chapter_batch` 接入前端 Agent run action descriptor registry。目标是让长篇批次真实执行结果在 Hermes 聊天中显示完成、阻塞与失败摘要，并明确章节写入、审批校验、资源绑定和下一步审查工具。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - 新增 `execute_longform_chapter_batch` action descriptor。
  - 新增 fallback label:
    - `长篇批次执行已完成`
    - `长篇批次执行已阻塞`
    - `长篇批次执行失败`
    - `长篇批次未找到`
    - `长篇批次执行中`
  - 从后端既有字段提取安全摘要：
    - 执行章节
    - 生成状态
    - 章节写入
    - 审批校验
    - 资源绑定
    - 阻塞原因
    - 错误摘要
    - 副作用数量
    - 下一步工具数量
  - 避免渲染 attempt/approval hash。
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - 覆盖 descriptor 识别、run id 提取、completed fallback、blocked fallback 和 failed fallback。
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

- `execute_longform_chapter_batch` 未被识别。
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
- 43 tests passed.

### T1 Regression

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 48 tests passed.

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

继续补 `review_longform_chapter_batch_execution` 聊天投影。原因：执行完成后，Agent 需要在对话中展示质量审查、连续性审查、世界模型证据是否齐全，以及是否应进入修订或下一批次。
