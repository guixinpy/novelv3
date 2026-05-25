# Agent World Model Route Phase74 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only Agent world-model route tool that summarizes current world profile readiness, confirmed fact coverage, subject-specific facts, and pending proposal pressure before generation or revision.

**Architecture:** Compose existing world model persistence and proposal review queue into one compact Agent-facing route. Keep it read-only. The route should tell the Agent whether it can proceed to preflight/generation or should stop and review world-model proposals first.

**Tech Stack:** SQLAlchemy models, world proposal review queue, Writing Agent tool registry/executor, pytest.

---

## Context

The long-term goal is to make Athena/world model a tool service for the Writing Agent. Existing APIs expose dashboard, projection, subject knowledge, snapshots, facts, and proposals, but the Agent needs a compact route-level answer:

- Is there a current world profile?
- How many confirmed facts are available?
- Does the target subject have relevant facts?
- Are pending proposals blocking generation?
- What tool should the Agent call next?

## Files

- Create `backend/app/services/writing_agent/agent_world_model_route.py`.
- Modify `backend/app/services/writing_agent/tool_registry.py`.
- Modify `backend/app/services/writing_agent/tool_executor.py`.
- Add `backend/tests/test_writing_agent_world_model_route.py`.
- Modify registry/executor tests.
- Add Phase74 report.

## Task 1: RED Registry And Executor Tests

- [ ] Add `inspect_agent_world_model_route` to expected tool names.
- [ ] Assert:

```python
assert target_type_for_tool("inspect_agent_world_model_route") == "agent_world_model_route"
assert "inspect_agent_world_model_route" in non_blocking_report_tool_names()
```

- [ ] Add executor metadata expectation:

```python
assert writing_agent_tool_adapter_metadata("inspect_agent_world_model_route") == {
    "tool_name": "inspect_agent_world_model_route",
    "adapter_type": "static",
    "category": "athena_world_model",
    "mutability": "read",
    "handler_name": "_inspect_agent_world_model_route",
}
```

## Task 2: Service Tests

- [ ] Missing profile:
  - project without `ProjectProfileVersion`;
  - output route status `blocked`;
  - recommended tool `import_setup_world_model`.
- [ ] Ready profile with confirmed fact:
  - profile + confirmed fact;
  - output route status `ready`;
  - fact count and subject facts are present.
- [ ] Pending proposal pressure:
  - profile + pending proposal item;
  - output route status `blocked`;
  - recommended tool `review_world_model_proposals`.

## Task 3: Implementation

- [ ] Create:

```python
def inspect_agent_world_model_route(
    db: Session,
    project_id: str,
    *,
    chapter_index: int | None = None,
    subject_ref: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
```

- [ ] Use latest `ProjectProfileVersion`.
- [ ] Use `build_world_proposal_agent_report()`.
- [ ] Query confirmed facts for current profile, optionally filtered by `subject_ref` and `chapter_index <= target`.
- [ ] Route:
  - `blocked/missing_world_model_profile` if no profile;
  - `blocked/pending_world_model_proposals` if proposal report has pending items;
  - `ready/world_model_ready` otherwise.
- [ ] Keep fact previews compact.

## Task 4: Verification

- [ ] Focused:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_world_model_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py -q -k "world_model_route or static_adapter_names_are_report_or_agent_native_tools or lists_unhandled_internal_tools_for_migration_tracking"
```

- [ ] Related:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_world_model_route.py tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_athena_longform.py tests\test_athena_retrieval.py -q
```

- [ ] Static checks:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

## Boundaries

Do:

- keep the route read-only;
- report proposal pressure clearly;
- keep fact previews compact;
- make the tool available to Agent planning.

Do not:

- apply or reject proposals;
- mutate world facts;
- call LLMs;
- add UI in this phase.
