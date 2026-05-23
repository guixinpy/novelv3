# Phase167 Longform Preflight Chat Projection Report

## Scope

本阶段将 `execute_longform_chapter_batch_preflight` 接入前端 Agent run action descriptor registry。目标是让长篇批次预检结果在 Hermes 聊天中显示为中文摘要，覆盖 ready 与 blocked 两类关键状态。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - 新增 `execute_longform_chapter_batch_preflight` action descriptor。
  - 新增 fallback label:
    - `长篇批次预检已就绪`
    - `长篇批次预检已阻塞`
    - `长篇批次未找到`
    - `长篇批次预检失败`
    - `长篇批次预检中`
  - 从后端既有字段提取安全摘要：
    - 预检章节
    - 就绪章节
    - 阻塞章节
    - 停止节点
    - 阻塞原因
    - 下一步工具数量
  - 避免渲染 plan hash 等内部字段。
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - 覆盖 descriptor 识别、run id 提取、ready fallback 和 blocked fallback。
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

- `execute_longform_chapter_batch_preflight` 未被识别。
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
- 34 tests passed.

### T1 Regression

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 39 tests passed.

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

继续补 `prepare_longform_chapter_batch_execution` 的聊天投影。原因：预检 ready 之后，下一步是固化为可审批的执行尝试清单；该工具会决定用户是否能在对话中明确看到执行清单、审批契约和风险边界。
