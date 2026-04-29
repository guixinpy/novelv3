# Prompt Orchestration

Production prompt assembly goes through `app.prompting.PromptAssembler` and `PROMPT_REGISTRY`.

## Prompt IDs

- Prompt IDs live in `backend/app/prompting/registry.py`.
- IDs use domain/action naming, for example `setup.generate`, `dialog.hermes`, `chapter.generate`.
- Each `PromptSpec` declares the template name, version, output type, required variables, and optional model defaults.
- Templates live in `backend/prompts/*.txt`. Registered production prompts must have a matching template file.

## Add A Prompt

1. Add the template under `backend/prompts/<template_name>.txt`.
2. Register a `PromptSpec` in `PROMPT_REGISTRY`.
3. Add sample variables in `backend/tests/test_prompting_static_quality.py` if the template introduces new variables.
4. Build it with `PromptAssembler().build("<prompt.id>", variables, context_blocks=...)`.
5. For generation payloads, include trace metadata from `build_prompt_trace_metadata()` or use the existing payload helpers.

Do not assemble production prompts with `app.core.prompt_manager.PromptManager`.

## Add A Context Provider

- Put provider helpers under `backend/app/prompting/providers/`.
- Return trace-compatible context blocks from `app.core.model_call_trace.build_context_block()`.
- Keep model-visible blocks separate from trace-only blocks when provider failures or diagnostics should not enter the model prompt.
- Sanitize provider failure details with `build_provider_error_block()` when exceptions may contain secrets.
- Wire providers at the API/core call site before `PromptAssembler().build(...)`.

## Trace Output

- Prompt metadata is stored in trace detail under `trace_metadata`: `prompt_id`, `prompt_version`, `template_name`, `template_hash`, and budget data when present.
- Context blocks are stored under `context_blocks`.
- View traces with:

```bash
curl "http://localhost:8000/api/v1/projects/<project_id>/model-call-traces"
curl "http://localhost:8000/api/v1/projects/<project_id>/model-call-traces/<trace_id>"
```

## Required Tests After Prompt Changes

Run the smallest relevant set:

```bash
cd backend
source .venv/bin/activate
pytest tests/test_prompt_templates.py tests/test_prompting_static_quality.py tests/test_prompting_contracts.py
```

Add migration-specific tests when changing a call site, for example `tests/test_prompting_generation_migration.py`, `tests/test_prompting_dialog_migration.py`, or `tests/test_prompting_chapter_migration.py`.

## Legacy PromptManager Boundary

`app.core.prompt_manager.PromptManager` is a legacy compatibility wrapper over `PromptRenderer`.
It may render templates by name for compatibility tests or old utility code, but production app code must not call it directly.
Use prompt IDs plus `PromptAssembler` and the registry instead.
