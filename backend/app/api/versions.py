from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ChapterContent, Outline, Project, Setup, Storyline, Version
from app.schemas import VersionCreate, VersionOut, VersionSummary

router = APIRouter(prefix="/api/v1/projects/{project_id}/versions", tags=["versions"])


@router.get("", response_model=list[VersionSummary])
def list_versions(project_id: str, node_type: str | None = None, node_id: str | None = None, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    q = db.query(Version).filter(Version.project_id == project_id)
    if node_type:
        q = q.filter(Version.node_type == node_type)
    if node_id:
        q = q.filter(Version.node_id == node_id)
    return q.order_by(Version.created_at.desc()).all()


@router.get("/{version_id}", response_model=VersionOut)
def get_version(project_id: str, version_id: str, db: Session = Depends(get_db)):
    v = db.query(Version).filter(Version.id == version_id, Version.project_id == project_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    return v


@router.post("", response_model=dict)
def create_version(project_id: str, payload: VersionCreate, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    max_num = db.query(func.max(Version.version_number)).filter(
        Version.project_id == project_id,
        Version.node_type == payload.node_type,
        Version.node_id == payload.node_id,
    ).scalar() or 0

    version = Version(
        project_id=project_id,
        node_type=payload.node_type,
        node_id=payload.node_id,
        version_number=max_num + 1,
        content=payload.content,
        description=payload.description,
        author=payload.author,
    )
    db.add(version)

    _apply_content_to_node(db, payload.node_type, payload.node_id, payload.content)

    db.commit()
    db.refresh(version)
    return {"version_saved": True, "version_id": version.id, "version_number": version.version_number}


@router.post("/{version_id}/rollback", response_model=dict)
def rollback_version(project_id: str, version_id: str, db: Session = Depends(get_db)):
    v = db.query(Version).filter(Version.id == version_id, Version.project_id == project_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")

    max_num = db.query(func.max(Version.version_number)).filter(
        Version.project_id == project_id,
        Version.node_type == v.node_type,
        Version.node_id == v.node_id,
    ).scalar() or 0

    new_version = Version(
        project_id=project_id,
        node_type=v.node_type,
        node_id=v.node_id,
        version_number=max_num + 1,
        content=v.content,
        description=f"Rollback to v{v.version_number}",
        author="user",
    )
    db.add(new_version)

    _apply_content_to_node(db, v.node_type, v.node_id, v.content)

    db.commit()
    db.refresh(new_version)
    return {"version_saved": True, "version_id": new_version.id, "version_number": new_version.version_number}


@router.delete("/{version_id}")
def delete_version(project_id: str, version_id: str, db: Session = Depends(get_db)):
    v = db.query(Version).filter(Version.id == version_id, Version.project_id == project_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    db.delete(v)
    db.commit()
    return {"deleted": True}


def _apply_content_to_node(db: Session, node_type: str, node_id: str, content: str):
    import json
    if node_type == "setup":
        node = db.query(Setup).filter(Setup.id == node_id).first()
        if node:
            data = json.loads(content)
            node.world_building = data.get("world_building", node.world_building)
            node.characters = data.get("characters", node.characters)
            node.core_concept = data.get("core_concept", node.core_concept)
    elif node_type == "storyline":
        node = db.query(Storyline).filter(Storyline.id == node_id).first()
        if node:
            data = json.loads(content)
            node.plotlines = data.get("plotlines", node.plotlines)
            node.foreshadowing = data.get("foreshadowing", node.foreshadowing)
    elif node_type == "outline":
        node = db.query(Outline).filter(Outline.id == node_id).first()
        if node:
            data = json.loads(content)
            node.chapters = data.get("chapters", node.chapters)
            node.plotlines = data.get("plotlines", node.plotlines)
    elif node_type == "chapter":
        node = db.query(ChapterContent).filter(ChapterContent.id == node_id).first()
        if node:
            node.content = content
