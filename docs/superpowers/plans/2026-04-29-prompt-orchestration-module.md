# Prompt Orchestration Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a dedicated prompt orchestration module that makes model-call prompts versioned, testable, traceable, and reusable across Hermes, Athena, setup/storyline/outline generation, and chapter generation.

**Architecture:** Keep `backend/prompts/*.txt` as template resources, but move all prompt selection, rendering, context assembly, budget decisions, few-shot insertion, style-rule insertion, and trace metadata into a new backend orchestration layer. Existing API endpoints will migrate one chain at a time so every phase can be verified before the next phase starts.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Alembic, Vue 3, Pinia, Vitest, model-call-traces, Athena world model, Athena retrieval.

---

## Non-Negotiable Delivery Rules

- Each phase must leave the product runnable.
- Each phase must include focused backend tests before implementation changes.
- Do not start the next phase while the previous phase has failing focused tests.
- Do not remove existing `backend/prompts/*.txt` templates until all direct callers are migrated.
- Do not put core prompt templates into the database in this plan.
- Do not let frontend prompt transparency regress while backend prompt assembly is migrated.
- Do not change model provider behavior unless a phase explicitly says so.
- Use Lore Commit Protocol if committing phase checkpoints.

## Final Target Shape

```text
backend/app/prompting/
  __init__.py
  contracts.py
  registry.py
  renderer.py
  assembler.py
  budget.py
  tracing.py
  providers/
    __init__.py
    project.py
    setup.py
    storyline.py
    outline.py
    chapter.py
    athena.py
    retrieval.py
    dialog.py
    style.py
    few_shot.py
```

`backend/prompts/*.txt` remains the template directory.

The intended call site after migration:

```python
payload = prompt_assembler.build(
    db=db,
    prompt_id="chapter.generate",
    project=project,
    inputs={"chapter_index": chapter_index, "extra_feedback": extra_feedback},
)

result = await ai_service.complete(
    payload.messages,
    temperature=payload.model_params.temperature,
    max_tokens=payload.model_params.max_tokens,
    model=payload.model_params.model,
)
```

The intended trace metadata after migration:

```json
{
  "prompt_id": "chapter.generate",
  "prompt_version": "v1",
  "template_name": "generate_chapter",
  "template_hash": "sha256:...",
  "budget": {
    "max_context_chars": 24000,
    "included_blocks": 8,
    "omitted_blocks": 2
  }
}
```

## File Structure

Backend files to create:

- `backend/app/prompting/contracts.py`: Pydantic/dataclass contracts for prompt specs, model params, build inputs, context blocks, budget reports, and build result.
- `backend/app/prompting/registry.py`: central prompt registry and prompt IDs.
- `backend/app/prompting/renderer.py`: template loading, `string.Template` rendering, missing-variable detection, template hash calculation.
- `backend/app/prompting/budget.py`: deterministic context ordering, truncation, and omitted-block reporting.
- `backend/app/prompting/assembler.py`: high-level `PromptAssembler.build()` entrypoint.
- `backend/app/prompting/tracing.py`: helpers that convert `PromptBuildResult` into `AIModelCallTrace` arguments.
- `backend/app/prompting/providers/*.py`: focused context providers.
- `backend/tests/test_prompting_contracts.py`: contract and registry tests.
- `backend/tests/test_prompting_generation_migration.py`: setup/storyline/outline migration tests.
- `backend/tests/test_prompting_chapter_migration.py`: chapter prompt migration tests.
- `backend/tests/test_prompting_dialog_migration.py`: Hermes/Athena chat migration tests.

Backend files to modify:

- `backend/app/core/prompt_manager.py`: keep as compatibility wrapper, but move strict rendering into `prompting.renderer`.
- `backend/app/core/model_call_trace.py`: keep sanitization, add support for prompt metadata if missing.
- `backend/app/api/setups.py`: use `PromptAssembler` for setup generation.
- `backend/app/api/storylines.py`: use `PromptAssembler` for storyline generation.
- `backend/app/api/outlines.py`: use `PromptAssembler` for outline generation.
- `backend/app/api/chapters.py`: use `PromptAssembler` for chapter generation.
- `backend/app/api/dialogs.py`: use `PromptAssembler` for Hermes/Athena chat payloads.
- `backend/app/core/chat_compaction.py`: use registry-backed prompt rendering.
- `backend/app/core/l2_extractor.py`: remove inline extraction prompt and register it.
- `backend/app/core/prompt_optimizer.py`: move style-rule generation behind `prompting.providers.style`.
- `backend/app/core/few_shot_library.py`: move few-shot formatting behind `prompting.providers.few_shot`.
- `backend/tests/test_prompt_templates.py`: expand into registry/static template tests.
- Existing focused tests in `backend/tests/test_setups.py`, `test_storylines.py`, `test_outlines.py`, `test_chapters.py`, `test_dialogs.py`, `test_athena_dialog.py`, `test_model_call_traces.py`.

Frontend files to modify late in the plan:

- `frontend/src/api/types.ts`: expose prompt metadata and budget reports if not already typed.
- `frontend/src/components/modelTrace/TraceSummary.vue`: display prompt ID/version/template hash.
- `frontend/src/components/modelTrace/ContextBlockList.vue`: display included/omitted budget status.
- `frontend/src/components/modelTrace/ModelTraceDrawer.vue`: add prompt metadata section.
- Focused Vitest tests for trace drawer display.

## Prompt IDs

Use stable IDs. Do not expose file names as public IDs.

| Prompt ID | Existing template | Output type |
| --- | --- | --- |
| `setup.generate` | `generate_setup.txt` | JSON |
| `storyline.generate` | `generate_storyline.txt` | JSON |
| `outline.generate` | `generate_outline.txt` | JSON |
| `chapter.generate` | `generate_chapter.txt` | plain text |
| `dialog.hermes` | `chat_hermes.txt` | chat |
| `dialog.athena` | `chat_athena.txt` | chat |
| `dialog.compact` | `compact_dialog_context.txt` | plain text |
| `project.diagnose` | `diagnose_project.txt` | JSON |
| `athena.extract_l2` | new `athena_extract_l2.txt` | JSON |

`chat_project_assistant.txt` must be classified during Phase 0. If unused, archive or delete only after tests prove no call site depends on it.

---

## Phase 0: Baseline Audit And Safety Net

**Purpose:** Lock current behavior before moving code.

**Files:**

- Modify: `backend/tests/test_prompt_templates.py`
- Create: `backend/tests/test_prompting_contracts.py`

- [ ] Add a test that enumerates every `backend/prompts/*.txt` file and every registered prompt ID.

Expected assertions:

```python
def test_registered_prompt_templates_exist():
    from app.prompting.registry import PROMPT_REGISTRY
    from app.prompting.renderer import default_prompts_dir

    prompts_dir = default_prompts_dir()
    for spec in PROMPT_REGISTRY.values():
        assert (prompts_dir / f"{spec.template_name}.txt").exists()
```

- [ ] Add a test that proves all currently used templates render without unresolved placeholders.

Expected assertions:

```python
def test_prompt_templates_render_without_unresolved_placeholders():
    from app.prompting.registry import PROMPT_REGISTRY
    from app.prompting.renderer import PromptRenderer

    renderer = PromptRenderer()
    sample_vars = {
        "name": "潮汐门",
        "genre": "科幻悬疑",
        "description": "记忆潮汐吞没城市。",
        "style": "冷峻",
        "complexity": "中等",
        "world_building": "{}",
        "characters": "[]",
        "core_concept": "{}",
        "storyline": "{}",
        "total_chapters": 10,
        "chapter_index": 1,
        "language": "zh-CN",
        "project_name": "潮汐门",
        "project_genre": "科幻悬疑",
        "project_description": "记忆潮汐吞没城市。",
        "project_phase": "设定阶段",
        "project_status": "active",
        "current_words": "0",
        "target_chapters": "10",
        "target_words": "30000",
        "completed_items": "无",
        "missing_items": "设定",
        "suggested_next_step": "preview_setup",
        "world_context": "暂无世界上下文",
        "profile_version": "1",
        "dialog_lines": "1. [user] 你好",
        "has_setup": "false",
        "has_storyline": "false",
        "has_outline": "false",
        "has_chapters": "false",
    }

    for spec in PROMPT_REGISTRY.values():
        rendered = renderer.render(spec.template_name, sample_vars)
        assert "${" not in rendered.content
        assert "{{" not in rendered.content
```

- [ ] Run focused tests.

```bash
cd backend && source .venv/bin/activate && pytest tests/test_prompt_templates.py tests/test_prompting_contracts.py -q
```

Expected: fail until Phase 1 creates `app.prompting`.

**Phase 0 exit gate:** current direct prompt behavior is documented by failing tests, and no production code has changed yet.

---

## Phase 1: Core Prompting Module Skeleton

**Purpose:** Introduce the orchestration contracts without migrating business endpoints yet.

**Files:**

- Create: `backend/app/prompting/__init__.py`
- Create: `backend/app/prompting/contracts.py`
- Create: `backend/app/prompting/registry.py`
- Create: `backend/app/prompting/renderer.py`
- Create: `backend/app/prompting/budget.py`
- Create: `backend/app/prompting/assembler.py`
- Create: `backend/app/prompting/tracing.py`
- Modify: `backend/app/core/prompt_manager.py`
- Test: `backend/tests/test_prompting_contracts.py`
- Test: `backend/tests/test_prompt_templates.py`

- [ ] Implement `PromptSpec`, `PromptBuildResult`, `PromptModelParams`, `PromptBudgetReport`, and `RenderedTemplate`.
- [ ] Implement `PROMPT_REGISTRY` with the IDs listed above, excluding `athena.extract_l2` until Phase 5 if the template file does not exist yet.
- [ ] Implement `PromptRenderer.render(template_name, variables)` with strict missing-variable errors.
- [ ] Implement `PromptRenderer.template_hash(template_name)` using SHA-256 of template content.
- [ ] Implement `PromptBudgeter.apply(blocks, max_chars)` with stable priority ordering and omitted-block reporting.
- [ ] Keep `PromptManager.load(name, variables)` working by delegating to `PromptRenderer`.
- [ ] Run focused tests.

```bash
cd backend && source .venv/bin/activate && pytest tests/test_prompt_templates.py tests/test_prompting_contracts.py -q
```

Expected: pass.

- [ ] Run compatibility tests for existing prompt callers.

```bash
cd backend && source .venv/bin/activate && pytest tests/test_setups.py tests/test_storylines.py tests/test_outlines.py tests/test_chapters.py tests/test_dialogs.py tests/test_athena_dialog.py -q
```

Expected: pass.

**Phase 1 exit gate:** new module exists, old callers still work, no API behavior changed.

---

## Phase 2: Migrate Setup, Storyline, And Outline Generation

**Purpose:** Move lower-risk JSON generation chains first.

**Files:**

- Create: `backend/app/prompting/providers/project.py`
- Create: `backend/app/prompting/providers/setup.py`
- Create: `backend/app/prompting/providers/storyline.py`
- Create: `backend/app/prompting/providers/outline.py`
- Modify: `backend/app/api/setups.py`
- Modify: `backend/app/api/storylines.py`
- Modify: `backend/app/api/outlines.py`
- Test: `backend/tests/test_prompting_generation_migration.py`
- Update existing focused tests as needed.

- [ ] Add tests that each migrated endpoint creates trace metadata with `prompt_id`, `prompt_version`, `template_name`, and `template_hash`.
- [ ] Add tests that existing context blocks remain present:
  - setup: `project_profile`, `generate_setup_template`
  - storyline: setup world/characters/core concept, template block
  - outline: setup context, storyline context, outline target, template block
- [ ] Implement context providers for project/setup/storyline/outline.
- [ ] Implement assembler branches for `setup.generate`, `storyline.generate`, and `outline.generate`.
- [ ] Replace local prompt construction in `setups.py`, `storylines.py`, and `outlines.py` with assembler output.
- [ ] Preserve `command_args` behavior as a `user_feedback` context block.
- [ ] Run focused backend tests.

```bash
cd backend && source .venv/bin/activate && pytest tests/test_setups.py tests/test_storylines.py tests/test_outlines.py tests/test_prompting_generation_migration.py tests/test_model_call_traces.py -q
```

Expected: pass.

- [ ] Run migration sanity check.

```bash
cd backend && source .venv/bin/activate && alembic current
```

Expected: current database revision prints one head and no migration error.

**Phase 2 exit gate:** setup/storyline/outline generation behaves the same externally, but trace metadata now identifies prompt IDs and versions.

---

## Phase 3: Migrate Chapter Generation

**Purpose:** Move the highest-value writing chain after the simpler generation chains are stable.

**Files:**

- Create: `backend/app/prompting/providers/chapter.py`
- Create: `backend/app/prompting/providers/athena.py`
- Create: `backend/app/prompting/providers/retrieval.py`
- Create: `backend/app/prompting/providers/style.py`
- Create: `backend/app/prompting/providers/few_shot.py`
- Modify: `backend/app/api/chapters.py`
- Modify: `backend/app/core/prompt_optimizer.py`
- Modify: `backend/app/core/few_shot_library.py`
- Test: `backend/tests/test_prompting_chapter_migration.py`
- Update: `backend/tests/test_chapters.py`
- Update: `backend/tests/test_athena_longform.py`
- Update: `backend/tests/test_athena_retrieval.py`

- [ ] Add tests for chapter prompt metadata:
  - `prompt_id == "chapter.generate"`
  - chapter index is passed through
  - template hash exists
  - budget report exists
- [ ] Add tests that existing chapter context survives migration:
  - setup world building
  - setup characters
  - outline chapter target
  - previous chapter summary when `chapter_index > 1`
  - Athena world context
  - retrieval evidence if available
  - style rules if project style config exists
  - few-shot examples if genre matches
- [ ] Implement chapter provider that returns typed context blocks instead of one large ad hoc string.
- [ ] Implement Athena provider that wraps `build_chapter_context_package()` output and records profile version.
- [ ] Implement retrieval provider that reuses existing Athena retrieval context.
- [ ] Implement style provider that replaces direct `PromptOptimizer.optimize()` usage at the chapter call site.
- [ ] Implement few-shot provider that replaces direct `FewShotExampleLibrary` usage at the chapter call site.
- [ ] Replace `_build_chapter_call_payload()` internals with `PromptAssembler.build("chapter.generate")`.
- [ ] Keep external API response unchanged.
- [ ] Run focused backend tests.

```bash
cd backend && source .venv/bin/activate && pytest tests/test_chapters.py tests/test_prompting_chapter_migration.py tests/test_athena_longform.py tests/test_athena_retrieval.py tests/test_model_call_traces.py -q
```

Expected: pass.

**Phase 3 exit gate:** chapter generation uses the orchestration module and trace drawer can still open generated-chapter context.

---

## Phase 4: Migrate Hermes And Athena Chat

**Purpose:** Make interactive chat prompts use the same prompt registry and context block model.

**Files:**

- Create: `backend/app/prompting/providers/dialog.py`
- Modify: `backend/app/api/dialogs.py`
- Modify: `backend/app/core/context_injection.py` only if needed to expose provider-friendly helpers.
- Test: `backend/tests/test_prompting_dialog_migration.py`
- Update: `backend/tests/test_dialogs.py`
- Update: `backend/tests/test_athena_dialog.py`

- [ ] Add tests for Hermes chat build result:
  - `prompt_id == "dialog.hermes"`
  - system message contains project phase/status
  - world context blocks are present
  - dialog history block is present
- [ ] Add tests for Athena chat build result:
  - `prompt_id == "dialog.athena"`
  - profile version is present
  - Athena world context blocks are present
  - dialog history block is present
- [ ] Replace `_build_chat_messages()` and `_build_chat_call_payload()` internals with assembler output.
- [ ] Preserve system-message behavior for historical `DialogMessage(role="system")`.
- [ ] Preserve chat compaction threshold behavior.
- [ ] Run focused backend tests.

```bash
cd backend && source .venv/bin/activate && pytest tests/test_dialogs.py tests/test_athena_dialog.py tests/test_prompting_dialog_migration.py tests/test_model_call_traces.py -q
```

Expected: pass.

**Phase 4 exit gate:** Hermes and Athena real model calls are assembled by the prompt module and trace transparency still works for both.

---

## Phase 5: Migrate Secondary Prompts And Inline Prompt Debt

**Purpose:** Remove remaining prompt islands after primary user-visible chains are stable.

**Files:**

- Create: `backend/prompts/athena_extract_l2.txt`
- Modify: `backend/app/core/l2_extractor.py`
- Modify: `backend/app/core/chat_compaction.py`
- Modify: `backend/app/api/projects.py` if `diagnose_project` is still directly loaded there.
- Modify: `backend/app/prompting/registry.py`
- Test: `backend/tests/test_prompting_contracts.py`
- Add or update focused tests for L2 extractor and compaction.

- [ ] Move `EXTRACTION_PROMPT` from `l2_extractor.py` into `backend/prompts/athena_extract_l2.txt`.
- [ ] Register `athena.extract_l2`.
- [ ] Replace direct `.format()` in `l2_extractor.py` with `PromptAssembler` or `PromptRenderer`.
- [ ] Register and verify `dialog.compact`.
- [ ] Register and verify `project.diagnose` if still active.
- [ ] Decide `chat_project_assistant.txt`:
  - if referenced by no call site, archive it under docs or delete it from active prompts;
  - if intended for future use, register it explicitly with a disabled/deprecated marker.
- [ ] Run prompt-wide tests.

```bash
cd backend && source .venv/bin/activate && pytest tests/test_prompt_templates.py tests/test_prompting_contracts.py tests/test_dialogs.py tests/test_athena_dialog.py -q
```

Expected: pass.

**Phase 5 exit gate:** no production AI prompt is hidden as a large inline string in backend code.

---

## Phase 6: Strengthen Trace Transparency UI

**Purpose:** Let users inspect not just raw messages, but also prompt identity and budget decisions.

**Files:**

- Modify: `backend/app/schemas/model_call_trace.py`
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/components/modelTrace/TraceSummary.vue`
- Modify: `frontend/src/components/modelTrace/ContextBlockList.vue`
- Modify: `frontend/src/components/modelTrace/ModelTraceDrawer.vue`
- Add or update frontend tests near existing model trace tests.

- [ ] Ensure trace detail response exposes:
  - prompt ID
  - prompt version
  - template name
  - template hash
  - included context block count
  - omitted context block count
  - truncation flags
- [ ] Add frontend display tests for prompt metadata.
- [ ] Add frontend display tests for omitted/truncated context blocks.
- [ ] Keep raw messages viewer unchanged.
- [ ] Run focused frontend tests.

```bash
cd frontend && npm run test:unit -- src/components/modelTrace src/stores/modelTraces.test.ts
```

Expected: pass.

**Phase 6 exit gate:** user-facing context transparency becomes prompt-aware without breaking existing trace drawer behavior.

---

## Phase 7: Static Prompt QA Gate

**Purpose:** Prevent future prompt regressions from entering silently.

**Files:**

- Create: `backend/tests/test_prompting_static_quality.py`
- Modify: `backend/tests/test_prompt_templates.py`
- Optionally create: `backend/app/prompting/quality.py`

- [ ] Add tests for:
  - every registered prompt has existing template file
  - every template renders with sample variables
  - every registered prompt has non-empty version
  - every registered prompt declares output type
  - JSON prompts have a parser or response-format expectation
  - no active production prompt contains unresolved `{{...}}`
  - no active production prompt contains `TODO` or `TBD`
- [ ] Add a test that scans `backend/app` for large inline prompt constants.

Allowed exceptions:

```python
ALLOWED_INLINE_PROMPT_FILES = {
    "backend/app/prompting/registry.py",
    "backend/app/prompting/providers/style.py",
    "backend/app/prompting/providers/few_shot.py",
}
```

- [ ] Run static prompt QA.

```bash
cd backend && source .venv/bin/activate && pytest tests/test_prompting_static_quality.py tests/test_prompt_templates.py -q
```

Expected: pass.

**Phase 7 exit gate:** future prompt changes fail fast when template variables, registry metadata, or inline prompt debt regress.

---

## Phase 8: Full Chain Regression And Dogfood

**Purpose:** Prove the migrated module works through the actual product flow.

**Backend verification:**

```bash
cd backend && source .venv/bin/activate && pytest -q
```

Expected: all backend tests pass.

**Frontend verification:**

```bash
cd frontend && npm run test:unit
cd frontend && npm run build
```

Expected: all frontend unit tests pass and production build succeeds.

**Manual dogfood path:**

- [ ] Start backend and frontend dev servers.
- [ ] Create a new project with target chapter count set to 3.
- [ ] Use Athena to generate/import setup.
- [ ] Generate storyline.
- [ ] Generate outline.
- [ ] Generate chapter 1.
- [ ] Open chapter generation trace and verify:
  - prompt ID is `chapter.generate`
  - prompt version is visible
  - template hash is visible
  - Athena context block is present
  - retrieval context block is present when indexed material exists
  - budget report is visible
- [ ] Send one Hermes chat message and verify trace opens.
- [ ] Send one Athena chat message and verify trace opens.
- [ ] Confirm no browser console errors during the above flow.

**Phase 8 exit gate:** whole creative chain runs with the new module and prompt transparency remains user-visible.

---

## Phase 9: Cleanup Legacy Prompt Paths

**Purpose:** Remove compatibility debt only after all behavior has been migrated and tested.

**Files:**

- Modify: `backend/app/core/prompt_manager.py`
- Modify or delete: unused prompt templates.
- Modify: docs that describe prompt architecture.
- Update: `docs/ai-call-context-transparency.md` or create a dedicated prompt module doc.

- [ ] Search for direct prompt loads.

```bash
rg -n "PromptManager\\(|\\.load\\(\" backend/app backend/tests -g '*.py'
```

Expected: either no production direct callers, or only compatibility tests.

- [ ] Search for inline prompt constants.

```bash
rg -n "[A-Z_]*PROMPT\\s*=|请以 JSON|你是|返回格式" backend/app -g '*.py'
```

Expected: no large production prompt constants outside `backend/app/prompting`.

- [ ] Remove or deprecate `PromptManager` direct usage.
- [ ] Document the final module:
  - prompt IDs
  - how to add a new prompt
  - how to add a context provider
  - how to inspect trace output
  - what tests must be run after prompt changes
- [ ] Run full verification again.

```bash
cd backend && source .venv/bin/activate && pytest -q
cd frontend && npm run test:unit
cd frontend && npm run build
```

Expected: pass.

**Phase 9 exit gate:** prompt orchestration is the only supported production prompt assembly path.

---

## Suggested Commit Boundaries

Commit only after a phase exit gate passes.

1. `Introduce prompt orchestration contracts`
2. `Route planning generation through prompt orchestration`
3. `Route chapter generation through prompt orchestration`
4. `Route Hermes and Athena chat through prompt orchestration`
5. `Migrate secondary prompts into prompt registry`
6. `Expose prompt metadata in model trace UI`
7. `Add static prompt quality gates`
8. `Document prompt orchestration workflow`

Every commit must use Lore Commit Protocol.

## Risk Register

| Risk | Where it can happen | Mitigation |
| --- | --- | --- |
| Prompt output subtly changes | Phases 2-4 | Assert existing context blocks and key prompt substrings before/after migration |
| Chapter quality regresses | Phase 3 | Dogfood chapter generation before cleanup |
| Trace drawer loses context | Phases 2-6 | Keep `context_blocks` shape backward compatible |
| Token budget cuts important facts | Phase 3 | Priority order: user request, chapter target, Athena facts, retrieval evidence, previous chapter, style, few-shot |
| JSON parsing gets worse | Phases 2 and 5 | Keep response format and existing parsers unchanged |
| Over-engineering | All phases | No database prompt CMS, no user-editable prompt console in this plan |
| Existing dirty workspace hides regressions | All phases | Check `git status --short` before phase commits and do not revert unrelated work |

## Definition Of Done

- All production AI calls use registered prompt IDs.
- Important traces include prompt ID, version, template name, template hash, and budget report.
- Setup/storyline/outline/chapter/Hermes/Athena/L2 extraction prompts are registered.
- Direct ad hoc prompt assembly is removed from API handlers.
- Backend full test suite passes.
- Frontend unit tests and build pass.
- Browser dogfood confirms trace drawer still exposes real prompt and context.
- Prompt module documentation exists for future contributors.
