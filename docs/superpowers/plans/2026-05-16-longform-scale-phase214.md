# Longform Scale Phase 214 - Use Lightweight Profile Refs In World Model Lists

## Goal

Avoid loading large `project_profile_versions.profile_payload` JSON on world-model list and validation endpoints that only need current profile identity.

## Problem

`world_model.py` has endpoints that need a current profile for filtering, but do not return the profile object:

- `GET /world-model/facts`
- `GET /world-model/proposal-bundles`
- `GET /world-model/proposal-review-queue`
- proposal review/split/rollback scope validation

These paths previously used `_get_current_profile()`, which materialized the full `ProjectProfileVersion` ORM row including `profile_payload`.

## Change

- Added local `ProjectProfileRef`.
- Added `_get_current_profile_ref()` selecting only:
  - `id`
  - `project_id`
  - `version`
  - `contract_version`
- Switched non-profile-returning list and scope-check paths to the lightweight helper.
- Left overview/dashboard/subject/snapshot paths on `_get_current_profile()` because their response schema returns `project_profile`.

## Regression Test

- `test_world_fact_list_current_profile_lookup_skips_profile_payload` verifies world fact list requests do not select `profile_payload`.

## Verification

Initial verification:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py::test_world_fact_list_current_profile_lookup_skips_profile_payload -q
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py -q
```

Results:

- Regression test: `1 passed`
- World frontend API tests: `40 passed`

Full verification is run before commit.
