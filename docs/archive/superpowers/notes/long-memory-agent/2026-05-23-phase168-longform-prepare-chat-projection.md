# Phase168 Longform Prepare Chat Projection Report

## Scope

本阶段将 `prepare_longform_chapter_batch_execution` 接入前端 Agent run action descriptor registry。目标是让长篇批次执行准备结果在 Hermes 聊天中显示审批与阻塞摘要，而不是裸露内部工具名。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - 新增 `prepare_longform_chapter_batch_execution` action descriptor。
  - 新增 fallback label:
    - `长篇批次执行准备待确认`
    - `长篇批次执行准备已阻塞`
    - `长篇批次未找到`
    - `长篇批次执行准备失败`
    - `长篇批次执行准备中`
  - 从后端既有字段提取安全摘要：
    - 执行章节
    - 审批状态
    - 写入步骤
    - 消费工具
    - 高风险副作用数量
    - 阻塞原因
    - 下一步工具数量
  - 避免渲染 attempt/approval/plan hash。
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - 覆盖 descriptor 识别、run id 提取、approval-required fallback 和 blocked fallback。
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

- `prepare_longform_chapter_batch_execution` 未被识别。
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
- 38 tests passed.

### T1 Regression

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 43 tests passed.

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

继续补 `execute_longform_chapter_batch` 聊天投影。原因：这是长篇批次链路中真正消费审批契约并写入章节、审查证据、世界模型提案的执行工具；聊天投影需要让用户明确看到执行状态、章节结果、证据数量和失败恢复路径。
