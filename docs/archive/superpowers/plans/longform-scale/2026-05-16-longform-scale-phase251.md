# Phase 251 - Model Trace Source Explanation Readability

## Goal

Improve long-form debugging readability in model traces. Query-aware retrieval
already stores explanations in source metadata, but the UI displayed internal
source type keys such as `longform_memory` and buried the retrieval explanation
inside raw JSON.

## TDD Evidence

- RED:
  - `npm run test:unit -- --run src/components/modelTrace/ContextSourceList.test.ts`
  - After setting the jsdom environment, failed because the rendered source list
    did not show `依据：...`, still displayed `longform_memory`, and exposed raw
    `explanation` JSON.
- GREEN:
  - Same focused command passed with `1 passed`.
  - `npm run test:unit -- --run src/components/modelTrace/ModelTraceDrawer.test.ts`
    passed with `8 passed`.

## Changes

- Source type keys now render as Chinese labels in model trace context sources:
  - `chapter` -> `章节正文`
  - `longform_memory` -> `长篇记忆`
  - `world_fact` -> `世界事实`
- Retrieval explanation metadata now renders as readable facts:
  - `依据：...`
  - `范围：...`
  - `得分：...`
- Raw metadata display removes the nested `explanation` object to avoid duplicate
  JSON noise.

## Verification Evidence

Fresh verification before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with `647 passed`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `416 passed`.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
