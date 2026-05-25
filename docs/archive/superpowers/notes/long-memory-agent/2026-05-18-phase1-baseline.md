# Phase 1 Baseline

## Source Snapshot

- Branch: `main`
- HEAD: `b76f6ce7b1ef704e56fea54dba243d81ea2bb271`
- Ahead/behind: `0 2` against `origin/main`; local `main` is ahead by two documentation commits.
- Active goal spec: `docs/superpowers/specs/2026-05-18-long-memory-writing-agent-goal.md`
- Active phase plan: `docs/superpowers/plans/long-memory-agent/2026-05-18-phase1-baseline-and-dogfood-protocol.md`
- Data snapshot: `data/mozhou.db` exists and is large enough to contain existing dogfood/project state; no destructive data action was taken.

## Existing Candidate Agent Tools

| Candidate Tool | Existing Files | Current Role | Risk / Gap |
| --- | --- | --- | --- |
| Hermes creation executor | `frontend/src/views/HermesView.vue`, `backend/app/prompting/providers/chapter.py`, `backend/prompts/generate_chapter.txt`, `backend/app/api/chapters.py` | Drives setup/storyline/outline/chapter creation and visible writing flows. | Not yet exposed as a typed Agent tool with explicit preconditions, result schema, and retry semantics. |
| Athena dialog | `backend/app/api/athena_dialog.py`, `backend/prompts/chat_athena.txt`, `frontend/src/components/athena/AthenaChatPanel.vue`, `frontend/src/stores/athena.chat.test.ts` | Provides Athena-facing conversation and context boundary behavior. | Still behaves like a module conversation, not the main long-memory writing Agent entrypoint. |
| World model | `backend/app/api/world_model.py`, `backend/app/core/world_projection.py`, `backend/app/core/world_proposal_service.py`, `backend/app/models/world_*.py`, `frontend/src/stores/worldModel.ts` | Stores novel-internal facts, projections, proposal bundles, and consistency constraints. | Must remain fact layer; future knowledge base must not bypass proposal governance. |
| Retrieval memory | `backend/app/core/athena_retrieval.py`, `backend/app/models/retrieval.py`, `backend/app/api/athena_retrieval_api.py`, `frontend/src/components/athena/RetrievalPanel.vue` | Indexes generated chapters and confirmed world facts for context recall. | Retrieval is available, but not yet a unified Agent memory router across project knowledge, author preferences, and writing patterns. |
| Longform memory | `backend/app/core/longform_memory.py`, `backend/app/models/longform_memory.py`, `backend/app/schemas/longform_memory.py`, `backend/tests/test_longform_scale.py` | Builds chapter/arc/volume/global memory layers for large works. | Good foundation for long text scale, but currently separated from user preference memory and reference-pattern memory. |
| Writing scheduler | `backend/app/core/writing_scheduler.py`, `backend/app/services/writing/writing_state_service.py`, `backend/app/models/writing_state.py`, `backend/app/api/writing.py` | Tracks writing state and continuous writing behavior. | Needs to become an Agent-callable execution lane with observable planning, cancellation, and recovery semantics. |
| Background tasks | `backend/app/services/tasks/background_task_service.py`, `backend/app/services/tasks/local_task_runner.py`, `backend/app/api/background_tasks_api.py`, `backend/app/models/background_task.py` | Provides task persistence and local async execution support. | Needs clear queues for generate/review/revise/reindex/knowledge-digest jobs. |
| Trace / context audit | `backend/app/core/model_call_trace.py`, `backend/app/models/ai_model_call_trace.py`, `backend/app/api/model_call_traces.py`, `frontend/src/stores/modelTraces.ts` | Records model calls, context blocks, prompt sources, and failure details. | Agent tool calls should produce comparable traces beyond raw model calls. |
| Athena review UI | `frontend/src/components/athena/ReviewInsightPanel.vue`, `frontend/src/components/athena/ProposalWorkbench.vue`, `frontend/src/components/athena/ConsistencyList.vue` | Surfaces proposals, consistency, and review-oriented signals. | Review is not yet a first-class automated quality loop for every generated chapter. |
| Knowledge viewer | `frontend/src/components/athena/KnowledgeViewer.vue`, `frontend/src/components/athena/SubjectKnowledgePanel.vue`, `backend/alembic/versions/20260429_add_subject_knowledge_fields.py` | Existing UI/model hooks for knowledge-like display and subject knowledge. | Does not yet satisfy the proposed knowledge base role: author memory, project strategy,拆书 patterns, and self-optimization experience. |
| Scale smoke | `scripts/longform_scale_smoke.py`, `backend/app/core/longform_scale_smoke.py`, `backend/tests/test_longform_scale.py` | Synthetic scale validation for thousand-chapter memory/retrieval/writing readiness. | Synthetic smoke cannot replace real longform dogfood with actual prose quality review. |

## Existing Verification Assets

| Area | Test / Script | Suggested Tier |
| --- | --- | --- |
| Longform memory and scale | `backend/tests/test_longform_scale.py`, `scripts/longform_scale_smoke.py` | T2 for module changes; T3 for milestone. |
| Athena retrieval | `backend/tests/test_athena_retrieval.py`, `frontend/src/components/athena/RetrievalPanel.test.ts`, `frontend/src/stores/athena.retrieval.test.ts` | T1/T2 depending on backend involvement. |
| World model | `backend/tests/test_world_*.py`, `frontend/src/stores/worldModel.test.ts`, `frontend/e2e/athena-world-model.spec.ts` | T2 for world model changes; T3 for migrations or projection changes. |
| Athena dialog | `backend/tests/test_athena_dialog.py`, `frontend/src/components/athena/AthenaChatPanel.test.ts`, `frontend/src/stores/athena.chat.test.ts` | T1 for prompt/UI boundary; T2 if backend payload changes. |
| Background tasks | `backend/tests/test_background.py`, `backend/tests/test_background_analyzer.py` | T1/T2 depending on queue scope. |
| Chapter generation | `backend/tests/test_chapters.py`, `backend/tests/test_prompting_chapter_migration.py`, `frontend/src/views/HermesView.test.ts` | T1 for prompt diagnostics; T2 for API/UI flow. |
| Model trace | `backend/tests/test_model_call_traces.py`, `frontend/src/stores/modelTraces.test.ts` | T1 for trace-only changes; T2 when new tool traces are added. |
| Full frontend build | `frontend/package.json`, `frontend/vite.config.ts` | T2/T3; avoid using for every documentation or tiny prompt change. |

## Immediate Observations

- novelv3 already has multiple strong building blocks: world model, retrieval memory, longform memory, background task service, model-call trace, and longform scale smoke.
- The missing center is not another isolated module; it is a Writing Agent Core that can treat those existing pieces as typed tools.
- Existing longform memory is chapter/arc/volume/global oriented. The next memory gap is author/project/reference-pattern memory.
- Existing synthetic scale smoke is valuable for performance and readiness, but the new goal must add real chapter generation dogfood to evaluate prose quality and user workflow.
- Current branch has two unpushed documentation commits. That is acceptable for Phase 1, but a checkpoint push should happen before large implementation work.

## Next Phase Inputs

- Use this baseline to define Agent tool contracts instead of inventing module names from scratch.
- Use `scripts/longform_scale_smoke.py` as a T2/T3 scale check, not as a substitute for real dogfood chapters.
- Start real dogfood only after the protocol document exists and the reference Agent study has identified memory/tool patterns worth adapting.
- Treat Knowledge Base as long-term creative memory, not as a replacement for Athena world facts.
