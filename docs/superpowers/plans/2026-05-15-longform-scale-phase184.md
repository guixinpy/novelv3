# Phase 184 - Add Proposal Item Status Queue Index

## Problem

Longform chapter analysis can create a large backlog of world-model proposal
items. Dashboard pending counts and the proposal review queue both filter by
project/profile and `item_status`, then order actionable items by chapter and
predicate. The table did not have a compound index for that access pattern.

## Change

- Added `ix_world_proposal_items_project_profile_status_order`.
- Covered project/profile/status filtering plus review queue ordering fields.
- Added an Alembic migration for existing databases.

## Tests

- RED: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_hot_tables_have_query_indexes -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_longform_scale.py::test_longform_hot_tables_have_query_indexes -q`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests\test_world_frontend_api.py::test_world_model_proposal_review_queue_clusters_low_risk_and_prioritizes_high_risk backend\tests\test_world_frontend_api.py::test_world_model_proposal_review_queue_limits_large_backlog backend\tests\test_world_frontend_api.py::test_world_model_proposal_review_queue_count_does_not_select_heavy_item_fields backend\tests\test_world_frontend_api.py::test_world_model_dashboard_uses_aggregate_metrics_without_loading_projection_rows -q`
- GREEN: `.\.venv\Scripts\python.exe -m alembic heads` from `backend`
- GREEN: `backend\.venv\Scripts\python.exe -m pytest backend\tests -q`
- GREEN: `npm run test:unit` from `frontend`
- GREEN: `npm run build` from `frontend`
- GREEN: `git diff --check`
- GREEN: DeepSeek key scan returned `NO_MATCH`

## Result

Review queue and dashboard pending-item reads now have a database index aligned
with the actionable proposal backlog access pattern.
