# Phase170 Longform Review Chat Projection Report

## Scope

本阶段将 `review_longform_chapter_batch_execution` 接入前端 Agent run action descriptor registry。目标是让长篇批次执行后审查结果在 Hermes 聊天中显示通过、阻塞与已记录摘要，帮助用户判断是否进入修订或下一批。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - 新增 `review_longform_chapter_batch_execution` action descriptor。
  - 新增 fallback label:
    - `长篇批次审查已通过`
    - `长篇批次审查已阻塞`
    - `长篇批次审查已记录`
    - `长篇批次审查失败`
    - `长篇批次未找到`
    - `长篇批次审查中`
  - 从后端既有字段提取安全摘要：
    - 审查章节
    - 审查闸门
    - 阻塞项
    - 警告项
    - 质量审查
    - 连续性审查
    - 世界模型
    - 阻塞或跳过原因
    - 下一步工具数量
  - 避免渲染内部 hash。
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - 覆盖 descriptor 识别、run id 提取、completed fallback、blocked fallback 和 skipped fallback。
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

- `review_longform_chapter_batch_execution` 未被识别。
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
- 48 tests passed.

### T1 Regression

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 53 tests passed.

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

继续补 `route_longform_chapter_batch_after_review` 聊天投影。原因：审查完成后，Agent 需要在对话中清楚展示是进入修订恢复，还是继续生成下一批章节。
