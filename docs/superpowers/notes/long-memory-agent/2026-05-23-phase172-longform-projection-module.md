# Phase172 Longform Projection Module Report

## Scope

本阶段将长篇批次 Agent run action projection 从 `agentRunProjection.ts` 拆到独立模块，目标是降低后续继续接入写作 Agent 工具时的单文件维护压力，同时保持 Hermes 聊天中的现有展示行为不变。

## Changes

- `frontend/src/components/chat/longformAgentRunProjection.ts`
  - 新增长篇批次 action type 列表：
    - `inspect_longform_chapter_batch`
    - `execute_longform_chapter_batch_preflight`
    - `prepare_longform_chapter_batch_execution`
    - `execute_longform_chapter_batch`
    - `review_longform_chapter_batch_execution`
    - `route_longform_chapter_batch_after_review`
  - 迁入所有长篇批次 action descriptor、fallback label、detail extraction 和长篇专用 helper。
- `frontend/src/components/chat/agentRunProjection.ts`
  - 保留通用 registry、恢复工具、Trace 审计和 run id 抽取逻辑。
  - 从新模块导入长篇 action type 与 descriptor，并组合进通用 registry。
  - 移除 `buildLongform*` helper 和长篇专用解析 helper。
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - 新增长篇模块导出契约测试，防止后续工具投影继续回流到通用文件。

## Validation

### RED

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Expected failure observed:

- `Failed to load url ./longformAgentRunProjection` because the dedicated module did not exist yet.

### GREEN

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Result:

- 1 test file passed.
- 32 tests passed.

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts
```

Result:

- 2 test files passed.
- 54 tests passed.

### T1 Regression

Command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 59 tests passed.

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

继续沿着“Agent 工具投影模块化”的方向推进。下一阶段优先检查后端 Agent 工具 registry 是否也存在长篇批次工具定义膨胀问题，必要时拆分为专门的 longform tool registry，并保持前后端 action type 契约一致。
