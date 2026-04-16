from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import Project, Setup, Outline, Topology
from app.schemas import TopologyOut
from app.core.topology_builder import TopologyBuilder

router = APIRouter(prefix="/api/v1/projects/{project_id}/topology", tags=["topologies"])


@router.get("", response_model=TopologyOut)
def get_topology(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    topology = db.query(Topology).filter(Topology.project_id == project_id).first()
    if topology:
        return topology

    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")

    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    builder = TopologyBuilder()
    data = builder.build(project_id, setup, outline)

    topology = Topology(**data)
    db.add(topology)
    db.commit()
    db.refresh(topology)
    return topology


@router.get("/character-graph")
def character_graph(project_id: str, db: Session = Depends(get_db)):
    topology = get_topology(project_id, db)
    nodes = [n for n in topology.nodes if n.get("type") == "CHARACTER"]
    edges = [e for e in topology.edges if e.get("type") in ("relationship", "appearance")]
    return {"nodes": nodes, "edges": edges}


@router.get("/timeline")
def timeline(project_id: str, db: Session = Depends(get_db)):
    topology = get_topology(project_id, db)
    nodes = [n for n in topology.nodes if n.get("type") == "EVENT"]
    nodes.sort(key=lambda x: x.get("meta", {}).get("chapter_index", 0))
    return {"events": nodes}
