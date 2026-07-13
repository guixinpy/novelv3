# Backend cleanup - remove v1 API layer

Remove the old v1 orchestration layer now that v2 agent API is complete.

## Deletion scope

1. api/dialogs.py — v1 chat API (1,912 lines, depends on run_service/intent_router)
2. api/writing_agent_runs.py — v1 run viewer
3. core/intent_router.py — intent routing for v1 (2,400 lines)
4. services/writing_agent/run_service.py — v1 run orchestrator (2,015 lines)
5. services/writing_agent/planner.py + recovery_planner + recommended_followup_planner
6. services/writing_agent/__init__.py (rewrite — remove run_service export)
7. Various support files only used by the above

## AC

- [ ] app/api/ no longer imports from deleted modules
- [ ] app/core/ no longer imports from deleted modules
- [ ] 932+ backend tests pass
