# 2026-05-26 Memory Tree Vertical Slice

## Goal Link

Active goal: complete the full Agent-native long-memory writing Agent upgrade from `docs/agent-native-guide/01-reference-patterns-report.md`.

This note covers Task 6 from `docs/superpowers/plans/2026-05-26-agent-native-long-memory-writing-agent.md`: introduce a Memory Tree projection and drill-down tool.

## Implemented

- Added `memory_tree.py` with an in-memory projection over existing `ChapterContent`, `Outline`, `Storyline`, and `LongformMemory`.
- The projection emits four deterministic levels: `volume`, `chapter`, `scene`, and `beat`.
- Scene and beat nodes keep source refs back to `LongformMemory` and relevant `ChapterContent`.
- Added `inspect_agent_memory_tree` descriptor and static adapter.
- Registered the tool in the existing Writing Agent tool registry and executor.

## Evidence

Focused tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_memory_tree.py -q
# 3 passed
```

## Remaining

- The tree is intentionally projection-only; no persistence table is added until dogfood proves the need.
- Scene/beat linkage currently uses existing chapter ranges and optional `scene_scope_key` metadata. Future generation tools should write richer parent refs when they create memories.
