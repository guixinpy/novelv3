import pytest

from app.api import dialogs
from app.core.context_injection import build_athena_world_context
from app.models import (
    DialogMessage,
    GenreProfile,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldProposalBundle,
    WorldProposalItem,
)


class _FakeAiResult:
    content = "世界模型已更新。"


async def _fake_complete(*args, **kwargs):
    return _FakeAiResult()


def _enable_fake_ai(monkeypatch):
    monkeypatch.setattr(dialogs, "load_api_key", lambda: True)
    monkeypatch.setattr(dialogs.ai_service, "complete", _fake_complete)


def _seed_project(db_session, *, with_profile: bool = False):
    project = Project(name="Athena Dialog", genre="玄幻")
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    profile_version = None
    if with_profile:
        genre_profile = GenreProfile(
            canonical_id=f"athena-dialog-{project.id}",
            display_name="通用",
            contract_version="world.contract.v1",
        )
        db_session.add(genre_profile)
        db_session.commit()

        profile_version = ProjectProfileVersion(
            project_id=project.id,
            genre_profile_id=genre_profile.id,
            version=1,
            contract_version="world.contract.v1",
            profile_payload={},
        )
        db_session.add(profile_version)
        db_session.commit()

    return project, profile_version


def test_athena_chat_rejects_empty_text_without_persisting_message(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project, _ = _seed_project(db_session)

    response = client.post(
        f"/api/v1/projects/{project.id}/athena/dialog/chat",
        json={"project_id": project.id, "text": "   "},
    )

    assert response.status_code == 422
    assert db_session.query(DialogMessage).count() == 0


def test_athena_chat_update_request_without_profile_does_not_claim_success(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project, _ = _seed_project(db_session)

    response = client.post(
        f"/api/v1/projects/{project.id}/athena/dialog/chat",
        json={
            "project_id": project.id,
            "text": "请把林舟设定为雾港城守夜人，并更新世界模型。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "世界模型已更新" not in payload["message"]
    assert "还没有建立正式 world-model profile" in payload["message"]
    assert payload["refresh_targets"] == []
    assert db_session.query(WorldProposalBundle).count() == 0
    assert db_session.query(WorldProposalItem).count() == 0


def test_athena_chat_update_request_with_profile_creates_reviewable_proposal(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project, profile_version = _seed_project(db_session, with_profile=True)
    text = "请把林舟设定为雾港城守夜人，并更新世界模型。"

    response = client.post(
        f"/api/v1/projects/{project.id}/athena/dialog/chat",
        json={"project_id": project.id, "text": text},
    )

    assert response.status_code == 200
    payload = response.json()
    assert "世界模型已更新" not in payload["message"]
    assert "待审提案" in payload["message"]
    assert payload["refresh_targets"] == ["proposals"]

    bundle = db_session.query(WorldProposalBundle).one()
    item = db_session.query(WorldProposalItem).one()
    assert bundle.project_profile_version_id == profile_version.id
    assert bundle.created_by == "athena.dialog"
    assert item.bundle_id == bundle.id
    assert item.object_ref_or_value == text
    assert item.item_status == "pending"


def test_athena_world_context_labels_setup_fallback_when_profile_is_missing(db_session):
    project, _ = _seed_project(db_session)
    db_session.add(
        Setup(
            project_id=project.id,
            characters=[{"name": "林舟"}],
            world_building={"background": "雾港城"},
            core_concept={"theme": "自我修正"},
        )
    )
    db_session.commit()

    context = build_athena_world_context(db_session, project.id)

    assert "尚未建立正式 world-model profile" in context
    assert "Setup 草稿" in context
    assert "林舟" in context
    assert "雾港城" in context
