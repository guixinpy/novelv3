# Phase105 Intent Projection Report Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `IntentRouter` 的自然语言匹配结果暴露为 Writing Agent 可检查的 intent projection/report，使系统能解释为什么某句低细节输入会路由到某个工具。

**Architecture:** 不替换现有 `IntentRouter`，而是在其内部增加可审计 projection 层。`resolve()` 继续返回原有 `ActionCandidate`，保证 API 行为兼容；新增 `project()` 返回结构化报告，包含匹配规则、诊断前置条件、提取参数、Agent route 和未匹配原因。Writing Agent 新增只读 inspect 工具读取该报告。

**Tech Stack:** Python dataclass、IntentRouter、ProjectDiagnosisOut、Writing Agent tool registry/executor、pytest。

---

## Context

Phase104 已让 slash/text/button 三类入口共享 `agent_route`。但自然语言 intent 仍由 `IntentRouter` 内部规则直接决定，Agent 无法解释“为什么这句话被路由到 `preview_chapter`”。长期目标要求低细节用户输入也能由 Agent 自主组织约束，因此需要先把规则路由变成可检查、可追踪的 projection/report。

本阶段只做 explainability 和 inspect，不引入 LLM planner，也不改变用户可见确认流程。

## Files

- Modify: `backend/app/core/intent_router.py`
  - 新增 `IntentProjection`。
  - 新增 `IntentRouter.project()`。
  - `IntentRouter.resolve()` 复用 projection，保持现有返回兼容。
- Modify: `backend/app/services/writing_agent/tool_registry.py`
  - 注册只读工具 `inspect_agent_intent_projection`。
- Modify: `backend/app/services/writing_agent/tool_executor.py`
  - 执行 `inspect_agent_intent_projection`。
- Modify: `backend/tests/test_dialogs.py`
  - 覆盖 `IntentRouter.project()` 的 rule、route、params、no match。
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
  - 覆盖 Agent inspect 工具。
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase105-intent-projection-report.md`
  - 阶段报告。

## Success Criteria

- `IntentRouter.resolve()` 原有行为不变。
- `IntentRouter.project()` 对章节生成输入返回：
  - `status=matched`
  - `rule_id`
  - `candidate`
  - `agent_route`
  - `diagnosis`
  - `extracted_params`
- 对普通闲聊返回 `status=no_match` 和明确 `reason`。
- Writing Agent 可通过 `inspect_agent_intent_projection` 获取同一结构化报告。
- 使用 T1 聚焦验证，不跑完整前后端测试。

## Tasks

### Task 1: Write failing tests for intent projection

**Files:**
- Modify: `backend/tests/test_dialogs.py`

- [ ] Add tests for setup intent projection.
- [ ] Add tests for chapter intent projection with chapter index extraction.
- [ ] Add tests for no-match projection.
- [ ] Run focused pytest and confirm failure before implementation.

Verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py -k "intent_router_projection or intent_router_action_candidate" -q
```

### Task 2: Implement IntentProjection

**Files:**
- Modify: `backend/app/core/intent_router.py`

- [ ] Add `IntentProjection` dataclass with `to_dict()`.
- [ ] Add `IntentRouter.project()`.
- [ ] Refactor internal rule branches to return projection before candidate.
- [ ] Keep `resolve()` compatible by returning `projection.candidate`.
- [ ] Re-run focused tests.

### Task 3: Add Writing Agent inspect tool

**Files:**
- Modify: `backend/app/services/writing_agent/tool_registry.py`
- Modify: `backend/app/services/writing_agent/tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`

- [ ] Add failing test for `inspect_agent_intent_projection`.
- [ ] Register descriptor.
- [ ] Execute projection from tool executor.
- [ ] Re-run focused executor tests.

### Task 4: Verify and report

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-22-phase105-intent-projection-report.md`

- [ ] Run T1 focused validation.
- [ ] Run `git diff --check`.
- [ ] Run targeted secret scan.
- [ ] Incorporate reference-project subagent findings if available.
- [ ] Write phase report.
- [ ] Commit and push `main`.

Verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialogs.py backend/tests/test_writing_agent_tool_executor.py -k "intent_router or intent_projection or inspect_agent_intent_projection" -q
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```
