# Memory Tree Quality Dogfood

## Runtime

- Date: 2026-06-04
- Source database: `data/agent_native_dogfood_20260526.db`
- Project: `3f85aed4-4f6f-413f-bd1a-03fbe02ea0f4`
- Read mode: SQLAlchemy read-only inspection against the isolated dogfood DB
- Tool: `inspect_agent_memory_tree_quality`

Purpose: turn the broad "Memory Tree summary quality still needs real longform
validation" gap into a concrete Agent-readable diagnostic.

## Tool Probe

```powershell
$env:MOZHOU_DATABASE_URL='sqlite:///D:/MyOP/CODE/NovelCodeSpace/novelv3/data/agent_native_dogfood_20260526.db'
@'
from app.db import SessionLocal
from app.services.writing_agent.memory_tree import inspect_agent_memory_tree_quality

project_id = "3f85aed4-4f6f-413f-bd1a-03fbe02ea0f4"
db = SessionLocal()
try:
    output = inspect_agent_memory_tree_quality(db, project_id, chapter_index=2, query="灯塔旧回声")
finally:
    db.close()
'@ | backend\.venv\Scripts\python -
```

## Output Summary

```text
status: degraded
volume_nodes: 1
chapter_nodes: 3
scene_nodes: 0
beat_nodes: 0
summary_backed_volume_nodes: 0
summary_backed_chapter_nodes: 0
summary_backed_chapter_ratio: 0.0
semantic_probe.status: missing_match
semantic_probe.query: 灯塔旧回声
semantic_probe.chapter_index: 2
recommended_next_tools:
- record_agent_memory_tree_summaries
- inspect_agent_memory_tree
- inspect_agent_dogfood_evidence
```

Diagnostics:

```text
memory_tree_summary_gap
memory_tree_semantic_probe_miss
```

## Interpretation

The real dogfood project has enough chapter content to project volume/chapter
nodes, but its archived DB predates the current `memory_tree_*_summary` memory
types. As a result, the new quality projection correctly reports that chapter
nodes are not backed by materialized Memory Tree summaries and that the semantic
probe cannot match the target clue.

This is not a runtime regression. It is a real validation finding: before
claiming Memory Tree semantic quality is complete, the Agent should route through
`prepare_record_agent_memory_tree_summaries` and
`execute_record_agent_memory_tree_summaries_with_approval` on real longform data,
then re-check `inspect_agent_memory_tree_quality`.
