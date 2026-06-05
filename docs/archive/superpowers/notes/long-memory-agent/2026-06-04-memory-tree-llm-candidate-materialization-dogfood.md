# Memory Tree LLM Candidate Materialization Dogfood

Date: 2026-06-04

## Purpose

Validate that an inspected Memory Tree LLM candidate trace can be materialized through a trace-bound approval contract, without bypassing the long-memory write gate. This run uses a deterministic fake model response on a temporary copy of the dogfood DB, so it proves approval, drift guard, write isolation, and quality recheck plumbing, not external model quality.

## Command

From `backend/`:

```powershell
$tmp = Join-Path $env:TEMP "agent_native_dogfood_llm_candidate_materialize_<random>.db"
Copy-Item -LiteralPath ..\data\agent_native_dogfood_20260526.db -Destination $tmp
$env:DOGFOOD_TMP_DB=$tmp
@'
import asyncio
import json
import os
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import LongformMemory
from app.services.writing_agent.approval_tool_metadata import build_approval_tool_metadata_by_name
from app.services.writing_agent.memory_tree import (
    MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
    inspect_agent_memory_tree_llm_candidates,
    summarize_agent_memory_tree_llm_candidate,
)
from app.services.writing_agent.memory_tree_summary_execution import (
    execute_record_agent_memory_tree_llm_candidate_summary_with_approval,
    prepare_record_agent_memory_tree_llm_candidate_summary,
)
from app.services.writing_agent.memory_tree_tool_adapters import build_memory_tree_tool_adapters

PROJECT_ID = "3f85aed4-4f6f-413f-bd1a-03fbe02ea0f4"
DB = os.environ["DOGFOOD_TMP_DB"]

class FakeAIService:
    async def complete(self, messages, **kwargs):
        return SimpleNamespace(
            content=json.dumps({
                "summary": "第2章围绕灯塔旧回声推进调查，林深与顾衍从蓝焰证词和暗道线索继续追索空白信来源，核心疑问仍未解开。",
                "salient_terms": ["灯塔旧回声", "蓝焰证词", "空白信来源"],
                "open_questions": ["空白信来源是否与灯塔暗道有关？"],
                "source_coverage": ["chapter_content", "outline", "storyline"],
            }, ensure_ascii=False),
            prompt_tokens=101,
            completion_tokens=66,
            model=kwargs.get("model") or "deepseek-chat",
        )

async def main():
    engine = create_engine(f"sqlite:///{DB}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        adapters = build_memory_tree_tool_adapters(approval_tool_metadata_provider=lambda plan: {})
        adapter_metadata_by_name = {name: adapter.to_metadata() for name, adapter in adapters.items()}
        def approval_metadata_provider(plan):
            return build_approval_tool_metadata_by_name(plan, adapter_metadata_by_name=adapter_metadata_by_name)

        before_memory_count = session.query(LongformMemory).filter(
            LongformMemory.project_id == PROJECT_ID,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        ).count()
        generated = await summarize_agent_memory_tree_llm_candidate(
            session,
            PROJECT_ID,
            chapter_index=2,
            query="灯塔旧回声",
            max_source_chars=1600,
            ai_service=FakeAIService(),
        )
        inspection = inspect_agent_memory_tree_llm_candidates(session, PROJECT_ID, chapter_index=2, limit=3)
        prepared = prepare_record_agent_memory_tree_llm_candidate_summary(
            session,
            PROJECT_ID,
            action_params={
                "candidate_trace_id": generated["trace"]["trace_id"],
                "quality_query": "灯塔旧回声",
            },
        )
        executed = execute_record_agent_memory_tree_llm_candidate_summary_with_approval(
            session,
            PROJECT_ID,
            action_params={
                "candidate_trace_id": generated["trace"]["trace_id"],
                "quality_query": "灯塔旧回声",
            },
            confirm_execute=True,
            approval_contract_hash=prepared["agent_plan_approval_contract_hash"],
            approval_contract=prepared["agent_plan_approval_contract"],
            approval_tool_metadata_provider=approval_metadata_provider,
        )
        after_memory_count = session.query(LongformMemory).filter(
            LongformMemory.project_id == PROJECT_ID,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        ).count()
        print(json.dumps({
            "generated_status": generated["status"],
            "inspection_status": inspection["status"],
            "prepare_status": prepared["status"],
            "execute_status": executed["status"],
            "candidate_trace_match": inspection["candidates"][0]["trace_id"] == generated["trace"]["trace_id"],
            "candidate_summary_chars": len(inspection["candidates"][0]["candidate"]["summary"]),
            "source_count": inspection["candidates"][0]["source_count"],
            "source_chars": inspection["candidates"][0]["source_chars"],
            "trace_status": inspection["candidates"][0]["trace_status"],
            "approval_verified": executed["agent_plan_approval_verification"]["status"] == "ready",
            "materialization_summary": executed["materialization"]["summary"],
            "post_quality_status": executed["post_materialization_quality"]["status"],
            "post_quality_summary_backed_chapter_nodes": executed["post_materialization_quality"]["coverage"]["summary_backed_chapter_nodes"],
            "post_quality_summary_backed_chapter_ratio": executed["post_materialization_quality"]["coverage"]["summary_backed_chapter_ratio"],
            "post_quality_semantic_probe_status": executed["post_materialization_quality"]["semantic_probe"]["status"],
            "post_quality_diagnostic_count": len(executed["post_materialization_quality"]["diagnostics"]),
            "memory_tree_summary_count_before": before_memory_count,
            "memory_tree_summary_count_after": after_memory_count,
            "inspection_recommended_next_tools": inspection["recommended_next_tools"],
            "execute_recommended_next_tools": executed["recommended_next_tools"],
        }, ensure_ascii=False, indent=2))
    finally:
        session.close()
        engine.dispose()

asyncio.run(main())
'@ | .\.venv\Scripts\python -
Remove-Item -LiteralPath $tmp
```

## Result

```json
{
  "generated_status": "ready",
  "inspection_status": "ready",
  "prepare_status": "approval_required",
  "execute_status": "success",
  "candidate_trace_match": true,
  "candidate_summary_chars": 49,
  "source_count": 3,
  "source_chars": 848,
  "trace_status": "success",
  "approval_verified": true,
  "materialization_summary": {
    "candidate_summary_nodes": 1,
    "created_nodes": 1,
    "updated_nodes": 0
  },
  "post_quality_status": "degraded",
  "post_quality_summary_backed_chapter_nodes": 1,
  "post_quality_summary_backed_chapter_ratio": 0.3333,
  "post_quality_semantic_probe_status": "matched",
  "post_quality_diagnostic_count": 1,
  "memory_tree_summary_count_before": 0,
  "memory_tree_summary_count_after": 1,
  "inspection_recommended_next_tools": [
    "prepare_record_agent_memory_tree_llm_candidate_summary",
    "execute_record_agent_memory_tree_llm_candidate_summary_with_approval",
    "inspect_agent_memory_tree_quality"
  ],
  "execute_recommended_next_tools": [
    "inspect_agent_memory_tree_quality"
  ]
}
```

## Interpretation

The candidate write path is now trace-bound and approval-gated: `prepare_record_agent_memory_tree_llm_candidate_summary` hashes the selected candidate payload into the Agent plan, and `execute_record_agent_memory_tree_llm_candidate_summary_with_approval` verifies the approval contract, mutation fingerprint, and resource binding before writing one chapter summary memory.

The postcheck remains `degraded` because this run materialized only chapter 2, leaving the other chapter summary gaps in the temporary copy. The semantic probe for `灯塔旧回声` is matched after the candidate summary write, proving the selected candidate can improve targeted Memory Tree recall without broad direct writes.

Remaining gaps: this still uses a fake model response, and single-candidate materialization does not close whole-project summary coverage. Next increments should run a real configured model and/or batch the candidate approval flow across the remaining chapter gaps.

## Follow-up Handoff Regression

The approval handoff now has concrete call payloads in addition to tool-name recommendations:

- `inspect_agent_memory_tree_llm_candidates` returns `recommended_next_tool_calls` entries for `prepare_record_agent_memory_tree_llm_candidate_summary`, one for each ready candidate trace in the inspection window, populated with the selected `candidate_trace_id`, `quality_chapter_index`, and a candidate salient term as `quality_query`.
- `prepare_record_agent_memory_tree_llm_candidate_summary` returns a `recommended_next_tool_calls` entry for `execute_record_agent_memory_tree_llm_candidate_summary_with_approval`, including `confirm_execute=true`, the approval contract/hash, and `requires_confirmation=true`.
- `prepare_record_agent_memory_tree_llm_candidate_summaries_batch` is covered by local regression tests: it accepts explicit candidate trace ids or an inspection window, builds per-candidate trace-bound approval contracts, and returns one `execute_record_agent_memory_tree_llm_candidate_summary_with_approval` handoff per ready candidate. It remains read-only.
- `execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval` is now available as a guarded batch executor: it accepts the prepared per-candidate execute payloads, requires a top-level confirmation, then reuses the single-candidate execute path for every item so each candidate still verifies its own approval contract, mutation fingerprint, and resource binding.
- After an approved single-candidate execute, `inspect_agent_memory_tree_llm_candidates` reports pending/materialized candidate counts from `LongformMemory`, marks the selected trace as materialized, stops recommending duplicate prepare calls for that trace, and `prepare_record_agent_memory_tree_llm_candidate_summary` blocks repeated prepare with `candidate_already_materialized`.

Targeted regression coverage:

```powershell
pytest tests/test_writing_agent_memory_tree.py::test_memory_tree_llm_candidate_trace_inspection_lists_persisted_candidates tests/test_writing_agent_memory_tree.py::test_prepare_record_memory_tree_llm_candidate_summary_builds_trace_bound_approval_contract tests/test_writing_agent_memory_tree.py::test_prepare_record_memory_tree_llm_candidate_summaries_batch_builds_per_candidate_contracts tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_memory_tree_llm_candidate_inspection tests/test_writing_agent_tool_registry.py::test_agent_tool_registry_includes_memory_tree_llm_candidate_summary_approval_chain
pytest tests/test_writing_agent_memory_tree.py::test_execute_record_memory_tree_llm_candidate_summaries_batch_with_approval_persists_each_candidate -q
pytest tests/test_writing_agent_memory_tree.py -q
```

## Frontend Handoff Regression

`AgentRunDrawer` now consumes `inspect_agent_memory_tree_llm_candidates` directly:

- It renders status, candidate/ready counts, chapter label, safe summary text, salient terms, source count/chars, and quality precheck status.
- It hides `candidate_trace_id`, `scope_key`, approval contract details, and other raw internal fields from the visible drawer.
- It reads the prepare `recommended_next_tool_calls` payloads and emits read-only `prepare_record_agent_memory_tree_llm_candidate_summary` continuations for multiple ready candidates, so the user can move from candidate inspection to approval preparation without hand-stitching trace ids.
- It renders safe candidate materialization labels such as pending/materialized/hash mismatch while still hiding trace ids, LongformMemory ids, and hashes. Materialized candidates do not get duplicate prepare buttons when the backend omits prepare tool calls.
- It also consumes `prepare_record_agent_memory_tree_llm_candidate_summaries_batch`, renders safe prepared/skipped counts and per-candidate quality query labels, and emits one `execute_record_agent_memory_tree_llm_candidate_summary_with_approval` payload per prepared candidate without showing trace ids or approval hashes.
- It consumes `execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval` output as a safe write summary, showing success/blocked counts, per-candidate chapter, create/update counts, and postcheck quality labels while hiding trace ids, approval hashes, approval verification objects, resource bindings, and LongformMemory ids.

Targeted regression coverage:

```powershell
npx vitest run src/components/writingAgent/AgentRunDrawer.test.ts -t "memory tree LLM candidate batch"
npx vitest run src/components/writingAgent/AgentRunDrawer.test.ts -t "memory tree LLM candidate batch execute"
npx vitest run src/components/writingAgent/AgentRunDrawer.test.ts -t "memory tree LLM candidate"
npx vitest run src/components/writingAgent/AgentRunDrawer.test.ts -t "memory tree LLM candidate prepare"
npx vitest run src/components/writingAgent/AgentRunDrawer.test.ts
```

## Dialog Handoff Regression

The Memory Tree LLM candidate chain is now reachable from the dialog control plane:

- `IntentRouter` maps natural language such as `准备第2章记忆树 LLM 摘要候选批量审批 limit 3` to `prepare_memory_tree_llm_candidate_summaries_batch`.
- `plan_dialog_intent_agent_run` maps Memory Tree LLM summary plan, candidate generation, candidate inspection, and batch prepare actions to direct read tool plans.
- The batch prepare route still only calls `prepare_record_agent_memory_tree_llm_candidate_summaries_batch`; it does not execute any write or bypass per-candidate confirmation.

Targeted regression coverage:

```powershell
pytest tests/test_dialogs.py::test_intent_router_projection_explains_memory_tree_llm_candidate_batch_prepare_route -q
pytest tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_dialog_intent_agent_plan_for_memory_tree_llm_reads tests/test_writing_agent_tool_executor.py::test_tool_executor_handles_dialog_intent_agent_plan_for_memory_tree_llm_candidate_batch_prepare -q
```
