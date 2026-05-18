# Reference Agent Study

## Scope

This note summarizes Phase 1 read-only analysis of local reference snapshots:

- `references/agent-projects/openclaw/`
- `references/agent-projects/hermes-agent/`
- `references/agent-projects/openhuman/`

The purpose is to extract design patterns for novelv3's long-memory writing Agent. These projects are references only; novelv3 should not depend on them or copy their broad general-purpose architecture.

## openclaw

### What To Learn

- Long memory should be split into root memory, indexed chunks, and retrieval interface. Relevant paths: `references/agent-projects/openclaw/src/memory/root-memory-files.ts`, `references/agent-projects/openclaw/packages/memory-host-sdk/src/host/memory-schema.ts`, `references/agent-projects/openclaw/packages/memory-host-sdk/src/host/types.ts`.
- Retrieval results should distinguish source and carry scores/citations, not come from one undifferentiated vector bucket. Relevant paths: `references/agent-projects/openclaw/packages/memory-host-sdk/src/host/types.ts`, `references/agent-projects/openclaw/packages/memory-host-sdk/src/host/memory-schema.ts`.
- Context assembly is a lifecycle, not prompt concatenation. Relevant paths: `references/agent-projects/openclaw/src/context-engine/types.ts`, `references/agent-projects/openclaw/src/context-engine/delegate.ts`.
- Active memory recall can run before context construction, but needs timeout, cache, allowlist, and fallback. Relevant paths: `references/agent-projects/openclaw/extensions/active-memory/index.ts`, `references/agent-projects/openclaw/extensions/active-memory/openclaw.plugin.json`.
- Tool visibility, permissions, and loop detection matter for an Agent that can call many tools. Relevant paths: `references/agent-projects/openclaw/src/tools/planner.ts`, `references/agent-projects/openclaw/src/agents/tool-policy.ts`, `references/agent-projects/openclaw/src/agents/tool-loop-detection.ts`.
- Commitments/open loops are highly relevant to foreshadowing and unresolved narrative promises. Relevant path: `references/agent-projects/openclaw/src/commitments/types.ts`.

### What Not To Copy

- Do not copy openclaw's full plugin ecosystem, communication integrations, or generic tool-discovery platform.
- Do not run an active-memory subagent before every small chat turn; novelv3 should trigger bounded memory recall at writing, outline, review, and consistency checkpoints.
- Do not copy QMD/vector/SQLite implementation details before novelv3 has its own domain memory contract.
- Do not build a full subagent control plane before the writing Agent has stable first-party tools.

### novelv3 Implications

- Define novelv3 memory sources in writing-domain terms: `world_bible`, `character_state`, `plot_threads`, `foreshadowing`, `chapter_history`, `user_preferences`, `writing_patterns`.
- Build context assembly as a pipeline: current chapter objective, recent prose, relevant memory recall, open loops, style constraints, generation task.
- Add an open-loop registry later for foreshadowing, unresolved promises, character commitments, and pending reveals.
- Keep Agent tools few and explicit at first: memory search, memory read, chapter plan, chapter write, continuity check, revision pass.

## hermes-agent

### What To Learn

- Agent loops need budgets and explicit exit reasons. Relevant paths: `references/agent-projects/hermes-agent/agent/conversation_loop.py`, `references/agent-projects/hermes-agent/agent/iteration_budget.py`.
- Tool calls should be validated before execution, including unknown tools, malformed JSON, and truncated arguments. Relevant path: `references/agent-projects/hermes-agent/agent/conversation_loop.py`.
- Internal state tools like todo, memory, session search, and delegation can be managed directly by the Agent loop. Relevant paths: `references/agent-projects/hermes-agent/model_tools.py`, `references/agent-projects/hermes-agent/agent/tool_executor.py`.
- Planning state can be lightweight: pending, in_progress, completed, cancelled. Relevant path: `references/agent-projects/hermes-agent/tools/todo_tool.py`.
- Context compression should preserve head, tail, and task state while summarizing the middle. Relevant paths: `references/agent-projects/hermes-agent/agent/context_compressor.py`, `references/agent-projects/hermes-agent/agent/conversation_compression.py`.
- Long recall can use FTS/session search with discovery, scroll, and browse modes rather than only vector recall. Relevant paths: `references/agent-projects/hermes-agent/hermes_state.py`, `references/agent-projects/hermes-agent/tools/session_search_tool.py`.

### What Not To Copy

- Do not copy the broad generic tool universe.
- Do not copy plugin context engine complexity in early phases.
- Do not model creative memory as only `MEMORY.md` or system prompt injection.
- Do not treat offline trajectory compression as runtime writing context compression.
- Do not prioritize cron/gateway automation before chapter generation, review, and memory stability.

### novelv3 Implications

- The writing Agent should return `completed`, `exit_reason`, and iteration/tool-call diagnostics after each run.
- Tool execution should have a small schema-checked registry before any LLM-directed orchestration is allowed.
- Chapter-writing compression should preserve novel-specific state: current chapter objective, character positions, active foreshadowing, immutable world facts, user preferences, and unresolved conflicts.
- Session lineage can map naturally to chapter batches, revision rounds, and review cycles.

## openhuman

### What To Learn

- Long memory should be layered, including memory docs, chunks, graph data, KV data, episodic FTS, and structured profile data. Relevant path: `references/agent-projects/openhuman/src/openhuman/memory/store/unified/init.rs`.
- User profile should be structured facets, not one prompt paragraph. Relevant path: `references/agent-projects/openhuman/src/openhuman/memory/store/unified/profile.rs`.
- Profile/preference injection should be filtered and limited. Relevant path: `references/agent-projects/openhuman/src/openhuman/learning/prompt_sections.rs`.
- Preferences need user-controlled states like pinned and forgotten. Relevant paths: `references/agent-projects/openhuman/src/openhuman/memory/store/unified/profile.rs`, `references/agent-projects/openhuman/src/openhuman/learning/schemas.rs`.
- Automatic semantic recall should be restrained to avoid memory echo and context pollution. Relevant path: `references/agent-projects/openhuman/src/openhuman/agent/memory_loader.rs`.
- Memory citations are important for trust and UI inspection. Relevant path: `references/agent-projects/openhuman/src/openhuman/agent/memory_loader.rs`.
- Memory ingest can be a pipeline: canonicalise, chunk, score, persist, extract, seal, topic/global digest. Relevant paths: `references/agent-projects/openhuman/src/openhuman/memory/tree/ingest.rs`, `references/agent-projects/openhuman/src/openhuman/memory/tree/store.rs`.
- Memory UI should expose source state, debug tools, search, reset/rebuild, and provenance. Relevant paths: `references/agent-projects/openhuman/app/src/components/intelligence/MemoryWorkspace.tsx`, `references/agent-projects/openhuman/app/src/components/settings/panels/MemoryDataPanel.tsx`, `references/agent-projects/openhuman/app/src/components/settings/panels/MemoryDebugPanel.tsx`.

### What Not To Copy

- Do not copy desktop/system-integration app state complexity.
- Do not copy external office/service sync systems.
- Do not make `PROFILE.md`/`MEMORY.md` the only truth.
- Do not copy the mascot/persona interface as novelv3's writing UI.
- Do not inject all memories into every prompt.

### novelv3 Implications

- Use structured profile facets for author preferences, writing taboos, genre expectations, and repeated user corrections.
- Add user-controlled memory states later: pinned, active, muted, forgotten.
- Require provenance for memory recalls so users can see why a preference, fact, or writing pattern was used.
- Translate topic/entity indexing into novel terms: character, faction, location, artifact, foreshadowing, plot thread.
- Provide a memory visibility/debug surface before trusting automated long-memory behavior.

## Cross-Project Patterns

- Long memory is layered, not a single prompt append.
- Good Agents distinguish current task state, user/project memory, session history, and domain facts.
- Retrieval needs source labels, citations, and limits.
- Context assembly is a lifecycle with pre-load, assemble, after-turn ingest, compaction, and resume behavior.
- Tool calling must be typed, gated, observable, and protected against loops.
- Planning state can begin lightweight, but must be structured enough to survive context compression.
- Memory UI/debuggability is not optional for trust in long-running Agents.
- Automatic recall must be bounded. Too much memory in every prompt degrades behavior.

## Recommended novelv3 Adaptation Principles

1. Keep Athena/world model as the internal story-fact authority.
2. Add Knowledge Base as creative memory: user preferences, project strategy, reference patterns, review lessons, and writing rules.
3. Build a small Writing Agent tool registry before broad orchestration.
4. Use source-scoped retrieval: chapters, world facts, longform memory, user preference facets, writing patterns, open loops.
5. Treat foreshadowing and unresolved promises as open loops with status.
6. Create a context assembly pipeline before replacing existing prompts.
7. Make every Agent run explain its inputs, tool calls, exit reason, and unresolved next step.
8. Use real dogfood chapter generation to decide which abstraction is actually needed.

## Open Questions For Later Phases

- Should the first Writing Agent Core live backend-only, or expose a thin frontend orchestration panel immediately?
- Should Knowledge Base start as database tables, markdown-backed memory, or an adapter over existing longform memory?
- How much of existing `LongformMemory` can be reused for creative memory without mixing it with world truth?
- What is the minimal tool schema for Phase 2: generation only, or generation plus review?
- Should open loops be implemented first as review notes, world proposals, or a new domain model?
- How should user-confirmed preferences be edited, forgotten, and cited in UI?
