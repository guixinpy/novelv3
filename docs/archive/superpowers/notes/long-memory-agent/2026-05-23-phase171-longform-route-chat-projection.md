# Phase171 Longform Route Chat Projection Report

## Scope

本阶段将 `route_longform_chapter_batch_after_review` 接入前端 Agent run action descriptor registry。目标是让长篇批次审查后的路由结果在 Hermes 聊天中显示为明确中文摘要：继续下一批、进入修订、阻塞或已记录。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - 新增 `route_longform_chapter_batch_after_review` action descriptor。
  - 新增 fallback label:
    - `长篇批次已路由到下一批`
    - `长篇批次已路由到修订`
    - `长篇批次路由已阻塞`
    - `长篇批次路由已记录`
    - `长篇批次路由失败`
    - `长篇批次未找到`
    - `长篇批次路由中`
  - 从后端既有字段提取安全摘要：
    - 路由章节
    - 路由决策
    - 下一章
    - 下一批
    - 修订动作
    - 阻塞或跳过原因
    - 下一步工具数量
  - 避免渲染内部 hash。
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - 覆盖 descriptor 识别、run id 提取、continue fallback、revision fallback 和 blocked fallback。
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

- `route_longform_chapter_batch_after_review` 未被识别。
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
- 53 tests passed.

### T1 Regression

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 58 tests passed.

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

长篇批次链路的聊天投影已经覆盖队列检查、预检、执行准备、执行、审查与路由。下一阶段建议转向收敛 `agentRunProjection.ts` 的可维护性：将长篇批次 descriptor 的 label/detail helpers 拆成独立模块，避免继续把所有 Agent 工具投影堆在单文件中。
