# 2026-05-26 Formal Provenance Schema Slice

## Goal Link

Active goal: complete the full Agent-native long-memory writing Agent upgrade from `docs/agent-native-guide/01-reference-patterns-report.md`.

This note covers Task 2 from `docs/superpowers/plans/2026-05-26-agent-native-long-memory-writing-agent.md`: formalize the provenance schema beyond a loose helper.

## Implemented

- Added `build_memory_provenance(...)` to `memory_provenance_contract.py`.
- The builder now validates:
  - non-empty `version`
  - non-empty `status`
  - `trace.source`
  - every source entry has `source_ref` and `source_type`
- The builder normalizes:
  - `source_count`
  - `sources`
  - `windows`
  - `recovery`
  - `trace.version`
- Migrated `agent_memory_route`, `agent_knowledge_base_route`, and `longform_context_summary` to call the explicit schema builder.
- Kept `ensure_memory_provenance_contract(...)` as a compatibility wrapper over the builder.

## Evidence

Focused schema tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_provenance_contract.py -q
# 3 passed
```

Route compatibility:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_provenance_contract.py backend\tests\test_writing_agent_memory_route.py backend\tests\test_writing_agent_knowledge_base_route.py backend\tests\test_writing_agent_runs.py -k provenance -q
# 6 passed, 191 deselected
```

Context/health regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_context_compression_projection.py backend\tests\test_writing_agent_health_projection.py -q
# 14 passed
```

Static diff check:

```powershell
git diff --check
# no output
```

## Remaining

- Provenance is still returned as JSON dictionaries; database persistence is not added.
- Future Memory Tree and worker slices should use `build_memory_provenance(...)` from their first implementation rather than recreating local provenance shapes.
- If provenance variants keep growing, the next step is explicit typed source/window/recovery dataclasses or Pydantic schemas.

