# Phase 215: Bound Storyline Setup Loading

## Goal

Reduce story line generation memory pressure for long-form projects by avoiding full `Setup` JSON materialization when only prompt-sized setup context is needed.

## Verification

- RED: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_storylines.py::test_generate_storyline_uses_bounded_setup_context_without_selecting_full_json -q`
  - Failed because `generate_storyline` selected full `setups.world_building`, `setups.characters`, and `setups.core_concept`.
- GREEN: same targeted test passes after switching to bounded SQL projections.
- Related: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_storylines.py -q`
  - `6 passed`

## Notes

- The API still sends setup context to the model, but each large JSON field is projected through `substr(cast(...))`.
- Serialized JSON snippets are normalized back to readable Chinese text before prompt assembly.
