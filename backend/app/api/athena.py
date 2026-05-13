from fastapi import APIRouter

from app.api import (
    athena_dialog,
    athena_evolution,
    athena_longform,
    athena_ontology,
    athena_optimization,
    athena_retrieval_api,
    athena_state,
)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/athena",
    tags=["athena"],
)

router.include_router(athena_optimization.router)
router.include_router(athena_ontology.router)
router.include_router(athena_state.router)
router.include_router(athena_evolution.router)
router.include_router(athena_retrieval_api.router)
router.include_router(athena_longform.router)
router.include_router(athena_dialog.router)
