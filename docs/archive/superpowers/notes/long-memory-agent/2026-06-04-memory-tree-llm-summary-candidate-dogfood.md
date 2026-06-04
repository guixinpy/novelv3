# Memory Tree LLM Summary Candidate Dogfood

Date: 2026-06-04

## Purpose

Validate that a real Memory Tree quality gap can execute the new traced LLM summary candidate path without writing chapter summary memories. This run uses a deterministic fake model response on a temporary copy of the dogfood DB, so it proves Trace/candidate plumbing and write isolation, not external model quality.

## Command

From `backend/`:

```powershell
$tmp = Join-Path $env:TEMP "agent_native_dogfood_llm_candidate_<random>.db"
Copy-Item -LiteralPath ..\data\agent_native_dogfood_20260526.db -Destination $tmp
$env:DOGFOOD_TMP_DB=$tmp
@'
import asyncio
import json
import os
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import AIModelCallTrace, LongformMemory
from app.services.writing_agent.memory_tree import MEMORY_TREE_CHAPTER_SUMMARY_TYPE, summarize_agent_memory_tree_llm_candidate

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
        before_memory_count = session.query(LongformMemory).filter(
            LongformMemory.project_id == PROJECT_ID,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        ).count()
        output = await summarize_agent_memory_tree_llm_candidate(
            session,
            PROJECT_ID,
            chapter_index=2,
            query="灯塔旧回声",
            max_source_chars=1600,
            ai_service=FakeAIService(),
        )
        trace = session.query(AIModelCallTrace).filter(AIModelCallTrace.id == output["trace"]["trace_id"]).one()
        after_memory_count = session.query(LongformMemory).filter(
            LongformMemory.project_id == PROJECT_ID,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        ).count()
        summary = {
            "status": output["status"],
            "target": output["summary_target"],
            "candidate_summary_chars": len(output["candidate"]["summary"]),
            "candidate_salient_terms": output["candidate"]["salient_terms"],
            "candidate_open_question_count": len(output["candidate"]["open_questions"]),
            "source_count": output["evidence_window"]["source_count"],
            "source_chars": output["evidence_window"]["source_chars"],
            "source_types": [source["source_type"] for source in output["evidence_window"]["sources"]],
            "trace_id_present": bool(output["trace"]["trace_id"]),
            "trace_type": trace.trace_type,
            "trace_status": trace.status,
            "trace_prompt_tokens": trace.prompt_tokens,
            "trace_completion_tokens": trace.completion_tokens,
            "trace_context_block_count": len(trace.context_blocks or []),
            "llm_call_executed": output["trace"]["llm_call_executed"],
            "memory_tree_summary_count_before": before_memory_count,
            "memory_tree_summary_count_after": after_memory_count,
            "side_effects": output["side_effects"],
            "recommended_next_tools": output["recommended_next_tools"],
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
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
  "status": "ready",
  "target": {
    "level": "chapter",
    "chapter_index": 2,
    "scope_key": "chapter:2",
    "memory_type": "memory_tree_chapter_summary"
  },
  "candidate_summary_chars": 49,
  "candidate_salient_terms": [
    "灯塔旧回声",
    "蓝焰证词",
    "空白信来源"
  ],
  "candidate_open_question_count": 1,
  "source_count": 3,
  "source_chars": 848,
  "source_types": [
    "chapter_content",
    "outline",
    "storyline"
  ],
  "trace_id_present": true,
  "trace_type": "memory_tree_summary_generation",
  "trace_status": "success",
  "trace_prompt_tokens": 101,
  "trace_completion_tokens": 66,
  "trace_context_block_count": 3,
  "llm_call_executed": true,
  "memory_tree_summary_count_before": 0,
  "memory_tree_summary_count_after": 0,
  "side_effects": {
    "executed": [
      "memory_tree_summary_generation_trace"
    ],
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

`summarize_agent_memory_tree_llm_candidate` now advances the prior LLM-ready plan into a traced candidate execution path. The trace is stored as `memory_tree_summary_generation`, carries three context blocks from real dogfood evidence, and records model token metadata.

The original dogfood DB is untouched, and the temporary copy still has `memory_tree_chapter_summary` count 0 after the run. Candidate materialization remains outside this path and must continue through the approval-gated summary write chain.

Remaining gap: this is a fake model response. A later increment should run a real configured model or add an approval-safe candidate persistence layer before using the candidate for summary materialization.
