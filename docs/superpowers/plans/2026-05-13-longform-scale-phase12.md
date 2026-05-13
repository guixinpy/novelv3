# Longform Scale Phase 12 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make prompt context budget pressure auditable for thousand-chapter writing, so users can see what was injected, what was omitted, and which blocks were budget-truncated.

**Architecture:** Extend the existing prompt budget report instead of adding a new subsystem. The backend budgeter will annotate budget-truncated blocks and report requested/used/remaining context characters; the trace schema and frontend trace drawer will surface those metrics in Chinese.

**Tech Stack:** Python dataclasses, FastAPI/Pydantic trace schemas, pytest, Vue 3, TypeScript, Vitest.

---

## File Structure

- Modify `backend/app/prompting/contracts.py`: add budget usage fields.
- Modify `backend/app/prompting/budget.py`: compute requested/used/remaining chars and annotate truncated blocks.
- Modify `backend/app/schemas/model_call_trace.py`: expose budget usage fields in trace detail.
- Modify `backend/tests/test_prompting_contracts.py`: cover backend budget usage and block truncation metadata.
- Modify `backend/tests/test_model_call_traces.py`: cover trace schema budget usage normalization.
- Modify `frontend/src/api/types.ts`: add budget usage fields.
- Modify `frontend/src/components/modelTrace/ContextBlockList.vue`: localize and display budget pressure.
- Modify `frontend/src/components/modelTrace/ModelTraceDrawer.vue`: parse legacy budget usage from raw metadata.
- Modify `frontend/src/components/modelTrace/ModelTraceDrawer.test.ts`: cover Chinese budget UI and usage metrics.

## Success Criteria

- Budget-truncated context blocks carry `truncated=true`, original character count, current character count, and recomputed token estimate.
- Prompt budget metadata includes `requested_context_chars`, `used_context_chars`, and `remaining_context_chars`.
- Trace detail schema exposes the new fields without breaking legacy trace metadata.
- Model trace drawer displays budget metrics in Chinese and shows used/max/remaining characters.
- Focused backend and frontend tests pass.
- Backend tests, frontend unit tests, frontend build, diff hygiene, and sensitive-key scans pass before commit.

## Task 1: Backend Budget Usage Metadata

**Files:**
- Modify: `backend/app/prompting/contracts.py`
- Modify: `backend/app/prompting/budget.py`
- Modify: `backend/app/schemas/model_call_trace.py`
- Test: `backend/tests/test_prompting_contracts.py`
- Test: `backend/tests/test_model_call_traces.py`

- [x] **Step 1: Write failing backend tests**

Add assertions that `PromptBudgeter` reports requested/used/remaining context characters and marks budget-truncated blocks as truncated. Add trace schema assertions that the new budget fields are derived from trace metadata.

- [x] **Step 2: Verify RED**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_contracts.py::test_budgeter_keeps_priority_but_returns_original_order_and_truncates backend\tests\test_model_call_traces.py::test_model_call_trace_detail_derives_prompt_metadata_and_budget_from_trace_metadata -v
```

Expected: FAIL because the new budget fields and block metadata are not implemented.

- [x] **Step 3: Implement minimal backend budget metadata**

Compute requested chars from all block contents, used chars from kept block contents, remaining chars from the budget, and update truncated block metadata.

- [x] **Step 4: Verify GREEN**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_contracts.py::test_budgeter_keeps_priority_but_returns_original_order_and_truncates backend\tests\test_model_call_traces.py::test_model_call_trace_detail_derives_prompt_metadata_and_budget_from_trace_metadata -v
```

Expected: PASS.

## Task 2: Frontend Trace Budget Visibility

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/components/modelTrace/ContextBlockList.vue`
- Modify: `frontend/src/components/modelTrace/ModelTraceDrawer.vue`
- Test: `frontend/src/components/modelTrace/ModelTraceDrawer.test.ts`

- [x] **Step 1: Write failing frontend test**

Update the model trace drawer test to expect Chinese budget labels and usage metrics such as `已注入 13 / 上限 24000 字` and `剩余 23987 字`.

- [x] **Step 2: Verify RED**

```powershell
npm --prefix frontend run test:unit -- src/components/modelTrace/ModelTraceDrawer.test.ts
```

Expected: FAIL because the current budget UI uses English labels and does not render usage metrics.

- [x] **Step 3: Implement frontend budget visibility**

Add typed budget fields, parse fallback metadata, and render Chinese labels in `ContextBlockList`.

- [x] **Step 4: Verify GREEN**

```powershell
npm --prefix frontend run test:unit -- src/components/modelTrace/ModelTraceDrawer.test.ts
```

Expected: PASS.

## Task 3: Verification and Commit

- [x] **Step 1: Focused tests**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_prompting_contracts.py backend\tests\test_model_call_traces.py -v
npm --prefix frontend run test:unit -- src/components/modelTrace/ModelTraceDrawer.test.ts
```

- [x] **Step 2: Full verification slice**

```powershell
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -v
npm --prefix frontend run test:unit
npm --prefix frontend run build
```

- [x] **Step 3: Hygiene checks**

```powershell
git diff --check
rg -n "<exact-sensitive-key>" .
rg -n "sk-[A-Za-z0-9_-]{20,}" .
git status --short
```

- [ ] **Step 4: Commit**

```powershell
git add backend/app/prompting/contracts.py backend/app/prompting/budget.py backend/app/schemas/model_call_trace.py backend/tests/test_prompting_contracts.py backend/tests/test_model_call_traces.py frontend/src/api/types.ts frontend/src/components/modelTrace/ContextBlockList.vue frontend/src/components/modelTrace/ModelTraceDrawer.vue frontend/src/components/modelTrace/ModelTraceDrawer.test.ts docs/superpowers/plans/2026-05-13-longform-scale-phase12.md
git commit -m "feat: expose prompt context budget pressure"
```
