import json
from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.api.deprecation import add_deprecation_header
from app.core.topology_builder import TopologyBuilder
from app.db import get_db
from app.models import Project, Setup, Topology
from app.schemas import TopologyOut

router = APIRouter(prefix="/api/v1/projects/{project_id}/topology", tags=["topologies"])
DEFAULT_TOPOLOGY_NODE_LIMIT = 200
DEFAULT_TOPOLOGY_EDGE_LIMIT = 500


@router.get("", response_model=TopologyOut)
def get_topology(
    project_id: str,
    db: Session = Depends(get_db),
    response: Response = None,
    node_offset: int = Query(0, ge=0),
    node_limit: int = Query(DEFAULT_TOPOLOGY_NODE_LIMIT, ge=1, le=1000),
    edge_offset: int = Query(0, ge=0),
    edge_limit: int = Query(DEFAULT_TOPOLOGY_EDGE_LIMIT, ge=1, le=2000),
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology/relations")
    _ensure_topology_exists(project_id, db)
    return _window_topology_from_db(
        db,
        project_id,
        node_offset=node_offset,
        node_limit=node_limit,
        edge_offset=edge_offset,
        edge_limit=edge_limit,
    )


def _load_or_create_topology(project_id: str, db: Session) -> Topology:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    topology = db.query(Topology).filter(Topology.project_id == project_id).first()
    if topology:
        return topology

    setup = db.query(Setup).filter(Setup.project_id == project_id).first()
    if not setup:
        raise HTTPException(status_code=404, detail="Setup not found")

    builder = TopologyBuilder()
    data = builder.build(project_id, setup, _iter_outline_chapters(db, project_id))

    topology = Topology(**data)
    db.add(topology)
    db.commit()
    db.refresh(topology)
    return topology


def _ensure_topology_exists(project_id: str, db: Session) -> None:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    topology_ref = db.query(Topology.id).filter(Topology.project_id == project_id).first()
    if topology_ref:
        return

    _load_or_create_topology(project_id, db)


def _iter_outline_chapters(db: Session, project_id: str) -> Iterator[dict[str, Any]]:
    rows = (
        db.execute(
            text(
                """
                SELECT chapter.value AS chapter_outline
                FROM outlines, json_each(outlines.chapters) AS chapter
                WHERE outlines.id = (
                    SELECT id
                    FROM outlines
                    WHERE project_id = :project_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                )
                ORDER BY CAST(chapter.key AS INTEGER)
                """
            ),
            {"project_id": project_id},
        )
        .mappings()
        .yield_per(100)
    )
    for row in rows:
        item = _decode_json_value(row["chapter_outline"])
        if isinstance(item, dict):
            yield item


def _decode_json_value(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _window_topology_from_db(
    db: Session,
    project_id: str,
    *,
    node_offset: int,
    node_limit: int,
    edge_offset: int,
    edge_limit: int,
) -> dict:
    row = (
        db.query(
            Topology.id.label("id"),
            Topology.project_id.label("project_id"),
            Topology.version.label("version"),
            Topology.indexes.label("indexes"),
            Topology.updated_at.label("updated_at"),
            func.coalesce(func.json_array_length(Topology.nodes), 0).label("nodes_total"),
            func.coalesce(func.json_array_length(Topology.edges), 0).label("edges_total"),
        )
        .filter(Topology.project_id == project_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Topology not found")

    metadata = row._mapping
    nodes_total = int(metadata["nodes_total"] or 0)
    edges_total = int(metadata["edges_total"] or 0)
    nodes = _window_topology_items(
        db,
        project_id,
        column_name="nodes",
        offset=node_offset,
        limit=node_limit,
    )
    edges = _window_topology_items(
        db,
        project_id,
        column_name="edges",
        offset=edge_offset,
        limit=edge_limit,
    )
    return {
        "id": metadata["id"],
        "project_id": metadata["project_id"],
        "version": metadata["version"],
        "nodes": nodes,
        "edges": edges,
        "indexes": _decode_json_value(metadata["indexes"]) or {},
        "nodes_total": nodes_total,
        "nodes_offset": node_offset,
        "nodes_limit": node_limit,
        "nodes_has_more": node_offset + node_limit < nodes_total,
        "edges_total": edges_total,
        "edges_offset": edge_offset,
        "edges_limit": edge_limit,
        "edges_has_more": edge_offset + edge_limit < edges_total,
        "updated_at": metadata["updated_at"],
    }


def _window_topology_items(
    db: Session,
    project_id: str,
    *,
    column_name: str,
    offset: int,
    limit: int,
    item_types: tuple[str, ...] | None = None,
    order_by: str = "CAST(item.key AS INTEGER)",
) -> list[dict[str, Any]]:
    if column_name not in {"nodes", "edges"}:
        raise ValueError(f"Unsupported topology column: {column_name}")

    type_filter, type_params = _topology_item_type_filter(item_types)
    params = {"project_id": project_id, "offset": offset, "limit": limit, **type_params}
    rows = db.execute(
        text(
            f"""
            SELECT item.value AS item
            FROM topologies, json_each(topologies.{column_name}) AS item
            WHERE topologies.project_id = :project_id{type_filter}
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
            """
        ),
        params,
    ).mappings()
    items: list[dict[str, Any]] = []
    for row in rows:
        item = _decode_json_value(row["item"])
        if isinstance(item, dict):
            items.append(item)
    return items


def _count_topology_items(
    db: Session,
    project_id: str,
    *,
    column_name: str,
    item_types: tuple[str, ...] | None = None,
) -> int:
    if column_name not in {"nodes", "edges"}:
        raise ValueError(f"Unsupported topology column: {column_name}")

    type_filter, type_params = _topology_item_type_filter(item_types)
    row = db.execute(
        text(
            f"""
            SELECT COUNT(1) AS total
            FROM topologies, json_each(topologies.{column_name}) AS item
            WHERE topologies.project_id = :project_id{type_filter}
            """
        ),
        {"project_id": project_id, **type_params},
    ).mappings().first()
    return int((row or {}).get("total") or 0)


def _topology_item_type_filter(item_types: tuple[str, ...] | None) -> tuple[str, dict[str, str]]:
    if not item_types:
        return "", {}

    params: dict[str, str] = {}
    placeholders: list[str] = []
    for index, item_type in enumerate(item_types):
        key = f"item_type_{index}"
        placeholders.append(f":{key}")
        params[key] = item_type
    return f" AND json_extract(item.value, '$.type') IN ({', '.join(placeholders)})", params


@router.get("/character-graph")
def character_graph(
    project_id: str,
    db: Session = Depends(get_db),
    response: Response = None,
    node_offset: int = Query(0, ge=0),
    node_limit: int = Query(DEFAULT_TOPOLOGY_NODE_LIMIT, ge=1, le=1000),
    edge_offset: int = Query(0, ge=0),
    edge_limit: int = Query(DEFAULT_TOPOLOGY_EDGE_LIMIT, ge=1, le=2000),
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology/character-graph")
    _ensure_topology_exists(project_id, db)
    character_types = ("CHARACTER",)
    edge_types = ("relationship", "appearance")
    nodes_total = _count_topology_items(db, project_id, column_name="nodes", item_types=character_types)
    edges_total = _count_topology_items(db, project_id, column_name="edges", item_types=edge_types)
    nodes = _window_topology_items(
        db,
        project_id,
        column_name="nodes",
        offset=node_offset,
        limit=node_limit,
        item_types=character_types,
    )
    edges = _window_topology_items(
        db,
        project_id,
        column_name="edges",
        offset=edge_offset,
        limit=edge_limit,
        item_types=edge_types,
    )
    return {
        "nodes": nodes,
        "edges": edges,
        "nodes_total": nodes_total,
        "nodes_offset": node_offset,
        "nodes_limit": node_limit,
        "nodes_has_more": node_offset + node_limit < nodes_total,
        "edges_total": edges_total,
        "edges_offset": edge_offset,
        "edges_limit": edge_limit,
        "edges_has_more": edge_offset + edge_limit < edges_total,
    }


@router.get("/timeline")
def timeline(
    project_id: str,
    db: Session = Depends(get_db),
    response: Response = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_TOPOLOGY_NODE_LIMIT, ge=1, le=1000),
):
    if response:
        add_deprecation_header(response, f"/api/v1/projects/{project_id}/athena/ontology/timeline")
    topology = _load_or_create_topology(project_id, db)
    nodes = [n for n in topology.nodes if n.get("type") == "EVENT"]
    nodes.sort(key=lambda x: x.get("meta", {}).get("chapter_index", 0))
    return {
        "events": nodes[offset:offset + limit],
        "total": len(nodes),
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < len(nodes),
    }
