from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.db import get_db
from app.models import Setup
from app.schemas import SetupOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/setup", tags=["setups"])


@router.get("", response_model=SetupOut)
def get_setup(project_id: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology")
    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")
    return setup
