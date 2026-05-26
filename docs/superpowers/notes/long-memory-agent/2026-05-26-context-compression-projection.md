# 2026-05-26 Context Compression Projection Slice

## Goal Link

Active goal: complete the full Agent-native long-memory writing Agent upgrade from `docs/agent-native-guide/01-reference-patterns-report.md`.

This note covers the first remaining 4.1 slice after control-loop hardening: context layered compression pre-diagnostics.

## Implemented

- Added `inspect_agent_context_compression_projection` as a read-only Agent projection.
- Projected chapter-window strategy, prompt-context budget usage, section truncation count, ContextGuard failure count, risks, recovery, and memory provenance.
- Registered the projection as `inspect_agent_context_compression_projection` in memory/trace descriptors and adapters.
- Wired the projection into `inspect_agent_health_projection` when `chapter_index` is provided.
- Added health diagnostics and recommended tools for context compression warnings/blocks.

## Evidence

Focused red/green tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_context_compression_projection.py -q
# 3 passed
```

Broader related tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_context_compression_projection.py backend\tests\test_writing_agent_health_projection.py backend\tests\test_writing_agent_tool_registry.py -q
# 81 passed

backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_tool_executor.py -q
# 159 passed
```

Static diff check:

```powershell
git diff --check
# no output
```

## Remaining

- The projection is diagnostic only. Actual layered compression and micro-compression are still future slices.
- ContextGuard failure count is an explicit tool parameter for now; later StopHooks/tool lifecycle work should derive it from run/step evidence.
- Dogfood still needs to prove whether this projection catches real longform context pressure during multi-chapter generation.

