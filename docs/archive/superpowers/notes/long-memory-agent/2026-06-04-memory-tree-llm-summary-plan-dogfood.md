# Memory Tree LLM Summary Plan Dogfood

Date: 2026-06-04

## Purpose

Validate that a real Memory Tree quality gap can be converted into a trace-required LLM summary plan without running a model or writing to `LongformMemory`.

## Command

From `backend/`:

```powershell
@'
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.services.writing_agent.memory_tree import build_agent_memory_tree_llm_summary_plan

DB = r"..\data\agent_native_dogfood_20260526.db"
PROJECT_ID = "3f85aed4-4f6f-413f-bd1a-03fbe02ea0f4"
engine = create_engine(f"sqlite:///{DB}")
Session = sessionmaker(bind=engine)
session = Session()
try:
    output = build_agent_memory_tree_llm_summary_plan(
        session,
        PROJECT_ID,
        chapter_index=2,
        query="灯塔旧回声",
        max_source_chars=1600,
    )
    summary = {
        "status": output["status"],
        "target": output["summary_target"],
        "source_count": output["evidence_window"]["source_count"],
        "source_chars": output["evidence_window"]["source_chars"],
        "source_types": [source["source_type"] for source in output["evidence_window"]["sources"]],
        "trace_required": output["llm_prompt_contract"]["trace_required"],
        "trace_type": output["llm_prompt_contract"]["trace_type"],
        "precheck_status": output["quality_gate"]["precheck"]["status"],
        "precheck_diagnostics": [item["code"] for item in output["quality_gate"]["precheck"].get("diagnostics", [])],
        "probe_status": output["quality_gate"]["precheck"]["semantic_probe"]["status"],
        "expected_postcheck": output["quality_gate"]["expected_postcheck"],
        "side_effects": output["side_effects"],
        "recommended_next_tools": output["recommended_next_tools"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
finally:
    session.close()
    engine.dispose()
'@ | .\.venv\Scripts\python -
```

## Result

```json
{
  "status": "ready",
  "target": {
    "level": "chapter",
    "chapter_index": 2,
    "scope_key": "chapter:2",
    "memory_type": "memory_tree_chapter_summary"
  },
  "source_count": 3,
  "source_chars": 848,
  "source_types": [
    "chapter_content",
    "outline",
    "storyline"
  ],
  "trace_required": true,
  "trace_type": "memory_tree_summary_generation",
  "precheck_status": "degraded",
  "precheck_diagnostics": [
    "memory_tree_summary_gap",
    "memory_tree_semantic_probe_miss"
  ],
  "probe_status": "missing_match",
  "expected_postcheck": {
    "tool_name": "inspect_agent_memory_tree_quality",
    "params": {
      "chapter_index": 2,
      "query": "灯塔旧回声"
    }
  },
  "side_effects": {
    "executed": [],
    "skipped": [
      "record_agent_memory_tree_summaries"
    ]
  },
  "recommended_next_tools": [
    "prepare_record_agent_memory_tree_summaries",
    "execute_record_agent_memory_tree_summaries_with_approval",
    "inspect_agent_memory_tree_quality"
  ]
}
```

## Interpretation

The original dogfood DB still reports a Memory Tree quality gap for chapter 2 and the semantic probe `灯塔旧回声`.

`build_agent_memory_tree_llm_summary_plan` converts that gap into a read-only evidence window and an LLM prompt contract with `trace_required=true` and `trace_type=memory_tree_summary_generation`. It does not mutate the DB. The recommended continuation is now traced candidate generation/inspection before any approval-gated summary materialization.

This is an LLM-ready planning layer, not the final LLM summary execution path. The next increment should run the model through the existing trace infrastructure and keep materialization behind the candidate-specific approval boundary.
