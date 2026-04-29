from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.world_contracts import ANNOTATION
from app.core.world_proposal_service import calculate_bundle_impact_scope, create_bundle, write_candidate_fact
from app.models import Project, ProjectProfileVersion
from app.schemas.world_proposals import ProposalCandidateFactCreate


WORLD_UPDATE_KEYWORDS = (
    "更新世界模型",
    "写入世界模型",
    "修改世界模型",
    "加入世界模型",
    "记录到世界模型",
    "新增",
    "设定为",
    "记住",
    "写入",
    "修正",
)

WORLD_UPDATE_NEGATION_MARKERS = (
    "不要",
    "别",
    "无需",
    "不需要",
    "不要直接",
    "先不要",
    "不要写入",
    "不要更新",
    "不要修改",
    "不要加入",
    "不要记录",
    "不要标记",
    "不要把",
    "不要将",
)


def require_project(db: Session, project_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )


def world_entity_type(item, fallback: str) -> str:
    raw_type = (
        getattr(item, "role_type", None)
        or getattr(item, "location_type", None)
        or getattr(item, "faction_type", None)
        or getattr(item, "artifact_type", None)
        or getattr(item, "resource_type", None)
        or fallback
    )
    labels = {
        "character": "角色",
        "setup_location": "地点",
        "setup_group": "势力",
        "setup_artifact": "物品",
        "characters": "角色",
        "locations": "地点",
        "factions": "势力",
        "artifacts": "物品",
        "resources": "资源",
    }
    return labels.get(raw_type, raw_type)


def world_entity_description(item) -> str:
    candidates = [
        getattr(item, "origin_background", None),
        getattr(item, "spatial_scope", None),
        getattr(item, "mission_or_doctrine", None),
        getattr(item, "function_summary", None),
        getattr(item, "notes", None),
    ]
    for value in candidates:
        text = str(value or "").strip()
        if not text:
            continue
        if text == "Imported from Setup world building":
            continue
        if text.startswith("Setup import from world_building."):
            _, _, fragment = text.partition(":")
            text = f"来源：Setup 世界设定。相关片段：{fragment.strip()}"
        return text
    return ""


def looks_like_world_update_request(text: str) -> bool:
    normalized = "".join(text.split())
    for keyword in WORLD_UPDATE_KEYWORDS:
        index = normalized.find(keyword)
        if index < 0:
            continue
        prefix = normalized[max(0, index - 8):index]
        if any(marker in prefix for marker in WORLD_UPDATE_NEGATION_MARKERS):
            continue
        return True
    return False


def create_dialog_world_update_proposal(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
    dialog_id: str,
    text: str,
):
    title = "Athena 对话待审世界更新"
    summary = text[:500]
    bundle = create_bundle(
        db=db,
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.dialog",
        title=title,
        summary=summary,
    )
    item = write_candidate_fact(
        db=db,
        bundle_id=bundle.id,
        created_by="athena.dialog",
        candidate=ProposalCandidateFactCreate(
            project_id=project_id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            contract_version=profile.contract_version,
            claim_id=f"athena.dialog.{uuid4()}",
            subject_ref="project.world_intake",
            predicate="user_proposed_update",
            object_ref_or_value=text,
            claim_layer="truth",
            evidence_refs=[f"dialog:{dialog_id}"],
            authority_type=ANNOTATION,
            confidence=0.5,
            notes="Athena 对话输入生成的待拆分世界模型提案，需人工审阅后才可进入真相层。",
        ),
    )
    calculate_bundle_impact_scope(db=db, bundle_id=bundle.id)
    return bundle, item
