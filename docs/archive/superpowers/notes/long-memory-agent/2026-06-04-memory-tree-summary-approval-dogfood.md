# Memory Tree Summary Approval Recheck Dogfood

## Runtime

- Date: 2026-06-04
- Source database: `data/agent_native_dogfood_20260526.db`
- Execution database: temporary SQLite copy, deleted after run
- Project: `3f85aed4-4f6f-413f-bd1a-03fbe02ea0f4`
- Tools:
  - `prepare_record_agent_memory_tree_summaries`
  - `execute_record_agent_memory_tree_summaries_with_approval`
  - `inspect_agent_memory_tree_quality`

Purpose: prove the Memory Tree summary gap found by
`2026-06-04-memory-tree-quality-dogfood.md` can be handled through an
approval-gated Agent write path and immediately re-checked by the quality
projection, without mutating the archived source database.

## Command

Run from `backend/`:

```powershell
@'
import asyncio
import json
import os
import shutil
import tempfile
from pathlib import Path

source = Path('../data/agent_native_dogfood_20260526.db').resolve()
fd, temp_name = tempfile.mkstemp(prefix='memory_tree_summary_dogfood_', suffix='.db')
os.close(fd)
temp_path = Path(temp_name)
shutil.copy2(source, temp_path)
os.environ['MOZHOU_DATABASE_URL'] = f"sqlite:///{temp_path.as_posix()}"

from app.db import SessionLocal, engine
from app.schemas.writing_agent import WritingAgentToolRequest
from app.services.writing_agent.memory_tree import inspect_agent_memory_tree_quality
from app.services.writing_agent.tool_adapter_types import WritingAgentToolContext
from app.services.writing_agent.tool_executor import execute_writing_agent_tool

project_id = '3f85aed4-4f6f-413f-bd1a-03fbe02ea0f4'

async def main():
    db = SessionLocal()
    try:
        before = inspect_agent_memory_tree_quality(db, project_id, chapter_index=2, query='灯塔旧回声')
        context = WritingAgentToolContext(db=db, project_id=project_id, run_id='dogfood-memory-tree-summary-approval')
        prepared = await execute_writing_agent_tool(
            context,
            WritingAgentToolRequest(
                tool_name='prepare_record_agent_memory_tree_summaries',
                params={'quality_chapter_index': 2, 'quality_query': '灯塔旧回声'},
            ),
        )
        executed = await execute_writing_agent_tool(
            context,
            WritingAgentToolRequest(
                tool_name='execute_record_agent_memory_tree_summaries_with_approval',
                params={
                    'quality_chapter_index': 2,
                    'quality_query': '灯塔旧回声',
                    'confirm_execute': True,
                    'approval_contract_hash': prepared.output['agent_plan_approval_contract_hash'],
                    'approval_contract': prepared.output['agent_plan_approval_contract'],
                },
            ),
        )
        after = inspect_agent_memory_tree_quality(db, project_id, chapter_index=2, query='灯塔旧回声')
        print(json.dumps({
            'before_status': before['status'],
            'before_summary_backed_chapter_nodes': before['coverage']['summary_backed_chapter_nodes'],
            'before_summary_backed_chapter_ratio': before['coverage']['summary_backed_chapter_ratio'],
            'before_probe_status': before['semantic_probe']['status'],
            'prepare_status': prepared.output['status'],
            'execute_status': executed.output['status'],
            'created_nodes': executed.output['materialization']['summary']['created_nodes'],
            'updated_nodes': executed.output['materialization']['summary']['updated_nodes'],
            'volume_summary_nodes': executed.output['materialization']['summary']['volume_summary_nodes'],
            'chapter_summary_nodes': executed.output['materialization']['summary']['chapter_summary_nodes'],
            'approval_verification_status': executed.output['agent_plan_approval_verification']['status'],
            'after_status': after['status'],
            'after_summary_backed_chapter_nodes': after['coverage']['summary_backed_chapter_nodes'],
            'after_summary_backed_chapter_ratio': after['coverage']['summary_backed_chapter_ratio'],
            'after_probe_status': after['semantic_probe']['status'],
            'after_probe_top_match_title': (after['semantic_probe']['top_match'] or {}).get('title'),
            'after_probe_top_match_score': (after['semantic_probe']['top_match'] or {}).get('score'),
            'after_diagnostics': after['diagnostics'],
        }, ensure_ascii=False, indent=2))
    finally:
        db.close()
        engine.dispose()
        temp_path.unlink(missing_ok=True)

asyncio.run(main())
'@ | .\.venv\Scripts\python -
```

## Output Summary

```text
before_status: degraded
before_summary_backed_chapter_nodes: 0
before_summary_backed_chapter_ratio: 0.0
before_probe_status: missing_match
prepare_status: approval_required
execute_status: success
created_nodes: 4
updated_nodes: 0
volume_summary_nodes: 1
chapter_summary_nodes: 3
approval_verification_status: ready
after_status: ready
after_summary_backed_chapter_nodes: 3
after_summary_backed_chapter_ratio: 1.0
after_probe_status: matched
after_probe_top_match_title: 第二章 被删去的证词
after_probe_top_match_score: 0.9
after_diagnostics: []
```

## Interpretation

The archived dogfood DB itself still predates Memory Tree summary materialization,
so direct read-only inspection starts in `degraded` state. On a temporary copy,
the approval chain first returns `approval_required`, then the approved executor
creates one volume summary and three chapter summaries. The follow-up quality
projection becomes `ready`: all three chapter nodes are backed by materialized
summary memory, and the semantic probe for `灯塔旧回声` matches chapter 2.

This validates the next safe operational path: when real projects report
`memory_tree_summary_gap`, the Agent should route through
`prepare_record_agent_memory_tree_summaries` and
`execute_record_agent_memory_tree_summaries_with_approval`, then re-check
`inspect_agent_memory_tree_quality`.
