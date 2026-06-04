# Memory Tree LLM Summary Candidate Dogfood

Date: 2026-06-04

## Purpose

Validate that a real Memory Tree quality gap can execute the new traced LLM summary candidate path without writing chapter summary memories, and that the generated candidate can be inspected later from `AIModelCallTrace.trace_metadata`. This run uses a deterministic fake model response on a temporary copy of the dogfood DB, so it proves Trace/candidate plumbing and write isolation, not external model quality.

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
from app.models import LongformMemory
from app.services.writing_agent.memory_tree import (
    MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
    inspect_agent_memory_tree_llm_candidates,
    summarize_agent_memory_tree_llm_candidate,
)

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
        generated = await summarize_agent_memory_tree_llm_candidate(
            session,
            PROJECT_ID,
            chapter_index=2,
            query="灯塔旧回声",
            max_source_chars=1600,
            ai_service=FakeAIService(),
        )
        inspection = inspect_agent_memory_tree_llm_candidates(
            session,
            PROJECT_ID,
            chapter_index=2,
            limit=3,
        )
        after_memory_count = session.query(LongformMemory).filter(
            LongformMemory.project_id == PROJECT_ID,
            LongformMemory.memory_type == MEMORY_TREE_CHAPTER_SUMMARY_TYPE,
        ).count()
        candidate = inspection["candidates"][0]
        summary = {
            "generated_status": generated["status"],
            "inspection_status": inspection["status"],
            "inspection_summary": inspection["summary"],
            "candidate_trace_match": candidate["trace_id"] == generated["trace"]["trace_id"],
            "candidate_summary_chars": len(candidate["candidate"]["summary"]),
            "candidate_salient_terms": candidate["candidate"]["salient_terms"],
            "source_count": candidate["source_count"],
            "source_chars": candidate["source_chars"],
            "quality_precheck_status": candidate["quality_precheck_status"],
            "trace_status": candidate["trace_status"],
            "prompt_tokens": candidate["prompt_tokens"],
            "completion_tokens": candidate["completion_tokens"],
            "memory_tree_summary_count_before": before_memory_count,
            "memory_tree_summary_count_after": after_memory_count,
            "inspection_recommended_next_tools": inspection["recommended_next_tools"],
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
  "generated_status": "ready",
  "inspection_status": "ready",
  "inspection_summary": {
    "candidate_traces": 1,
    "ready_candidates": 1
  },
  "candidate_trace_match": true,
  "candidate_summary_chars": 49,
  "candidate_salient_terms": [
    "灯塔旧回声",
    "蓝焰证词",
    "空白信来源"
  ],
  "source_count": 3,
  "source_chars": 848,
  "quality_precheck_status": "degraded",
  "trace_status": "success",
  "prompt_tokens": 101,
  "completion_tokens": 66,
  "memory_tree_summary_count_before": 0,
  "memory_tree_summary_count_after": 0,
  "inspection_recommended_next_tools": [
    "prepare_record_agent_memory_tree_summaries",
    "execute_record_agent_memory_tree_summaries_with_approval",
    "inspect_agent_memory_tree_quality"
  ]
}
```

## Interpretation

`summarize_agent_memory_tree_llm_candidate` now advances the prior LLM-ready plan into a traced candidate execution path. The trace is stored as `memory_tree_summary_generation`, carries three context blocks from real dogfood evidence, records model token metadata, and persists the normalized candidate payload under `trace_metadata.memory_tree_llm_summary_candidate.candidate`.

`inspect_agent_memory_tree_llm_candidates` can later recover that candidate from Trace metadata by chapter, proving the candidate is no longer only available in the immediate tool return.

The original dogfood DB is untouched, and the temporary copy still has `memory_tree_chapter_summary` count 0 after the run. Candidate materialization remains outside this path and must continue through the approval-gated summary write chain.

Remaining gap: this is a fake model response. A later increment should run a real configured model or add an approval-safe candidate persistence layer before using the candidate for summary materialization.
