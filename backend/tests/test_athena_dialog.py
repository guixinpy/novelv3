import pytest

from app.api import dialogs
from app.core.context_injection import build_athena_world_context, build_athena_world_context_blocks
from app.models import (
    AIModelCallTrace,
    Dialog,
    DialogMessage,
    GenreProfile,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldCharacter,
    WorldFactClaim,
    WorldProposalBundle,
    WorldProposalItem,
)


class _FakeAiResult:
    content = "世界模型已更新。"
    prompt_tokens = 222
    completion_tokens = 33


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
    assert payload["trace_id"] is None
    assert db_session.query(AIModelCallTrace).count() == 0
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
    assert payload["trace_id"] is None
    assert db_session.query(AIModelCallTrace).count() == 0

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


def test_athena_world_context_blocks_include_record_sources(db_session):
    project, profile_version = _seed_project(db_session, with_profile=True)
    character = WorldCharacter(
        project_id=project.id,
        profile_version=profile_version.version,
        character_id="character.linzhou",
        canonical_id="character.linzhou",
        primary_alias="林舟",
        name="林舟",
        aliases=["守夜人"],
        role_type="protagonist",
        identity_anchor="雾港城守夜人",
        contract_version=profile_version.contract_version,
    )
    fact = WorldFactClaim(
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        claim_id="fact.linzhou.role",
        chapter_index=3,
        subject_ref="character.linzhou",
        predicate="role",
        object_ref_or_value="雾港城守夜人",
        claim_layer="truth",
        claim_status="confirmed",
        authority_type="authoritative_structured",
        confidence=1.0,
        contract_version=profile_version.contract_version,
    )
    db_session.add_all([character, fact])
    db_session.commit()

    blocks = build_athena_world_context_blocks(db_session, project.id)

    assert any(block["kind"] == "world_entity" for block in blocks)
    fact_block = next(block for block in blocks if block["kind"] == "world_fact")
    assert fact_block["sources"][0]["source_type"] == "WorldFactClaim"
    assert fact_block["sources"][0]["source_id"] == fact.id
    assert fact_block["sources"][0]["chapter_index"] == 3


def test_athena_world_fact_context_block_sources_are_stably_ordered(db_session):
    project, profile_version = _seed_project(db_session, with_profile=True)
    later_fact = WorldFactClaim(
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        claim_id="fact.b",
        chapter_index=2,
        intra_chapter_seq=2,
        subject_ref="character.b",
        predicate="role",
        object_ref_or_value="后出现",
        claim_layer="truth",
        claim_status="confirmed",
        authority_type="authoritative_structured",
        confidence=1.0,
        contract_version=profile_version.contract_version,
    )
    earlier_fact = WorldFactClaim(
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        claim_id="fact.a",
        chapter_index=1,
        intra_chapter_seq=1,
        subject_ref="character.a",
        predicate="role",
        object_ref_or_value="先出现",
        claim_layer="truth",
        claim_status="confirmed",
        authority_type="authoritative_structured",
        confidence=1.0,
        contract_version=profile_version.contract_version,
    )
    db_session.add_all([later_fact, earlier_fact])
    db_session.commit()

    blocks = build_athena_world_context_blocks(db_session, project.id)

    fact_block = next(block for block in blocks if block["kind"] == "world_fact")
    assert [source["source_id"] for source in fact_block["sources"]] == [
        earlier_fact.id,
        later_fact.id,
    ]


def test_build_chat_call_payload_returns_messages_and_context_blocks_without_changing_messages(db_session):
    project, _ = _seed_project(db_session, with_profile=True)
    diagnosis = dialogs._build_diagnosis(db_session, project.id)
    hermes_dialog = Dialog(project_id=project.id, dialog_type="hermes")
    athena_dialog = Dialog(project_id=project.id, dialog_type="athena")
    db_session.add_all([hermes_dialog, athena_dialog])
    db_session.commit()
    db_session.add_all(
        [
            DialogMessage(dialog_id=hermes_dialog.id, role="user", content="Hermes 问题"),
            DialogMessage(dialog_id=athena_dialog.id, role="user", content="Athena 问题"),
        ]
    )
    db_session.commit()

    hermes_messages = dialogs._build_chat_messages(
        db_session,
        hermes_dialog.id,
        project,
        diagnosis,
        dialog_type="hermes",
    )
    athena_messages = dialogs._build_chat_messages(
        db_session,
        athena_dialog.id,
        project,
        diagnosis,
        dialog_type="athena",
    )

    hermes_payload = dialogs._build_chat_call_payload(
        db_session,
        hermes_dialog.id,
        project,
        diagnosis,
        dialog_type="hermes",
    )
    athena_payload = dialogs._build_chat_call_payload(
        db_session,
        athena_dialog.id,
        project,
        diagnosis,
        dialog_type="athena",
    )

    assert hermes_payload["messages"] == hermes_messages
    assert athena_payload["messages"] == athena_messages
    assert isinstance(hermes_payload["context_blocks"], list)
    assert isinstance(athena_payload["context_blocks"], list)
    assert hermes_payload["context_blocks"][-1]["kind"] == "dialog_history"
    assert hermes_payload["context_blocks"][-1]["sources"][0]["source_type"] == "Dialog"
    assert hermes_payload["context_blocks"][-1]["sources"][0]["source_id"] == hermes_dialog.id


def test_athena_chat_success_records_model_call_trace(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project, profile_version = _seed_project(db_session, with_profile=True)
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile_version.id,
            profile_version=profile_version.version,
            claim_id="fact.trace.role",
            subject_ref="character.linzhou",
            predicate="role",
            object_ref_or_value="雾港城守夜人",
            claim_layer="truth",
            claim_status="confirmed",
            authority_type="authoritative_structured",
            confidence=1.0,
            contract_version=profile_version.contract_version,
        )
    )
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{project.id}/athena/dialog/chat",
        json={"project_id": project.id, "text": "请分析林舟当前世界模型状态。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["trace_id"]

    detail_response = client.get(f"/api/v1/projects/{project.id}/model-call-traces/{payload['trace_id']}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["trace_type"] == "athena_chat"
    assert detail["status"] == "success"
    assert detail["prompt_tokens"] == 222
    assert any(
        block["kind"] in {"setup", "world_fact", "world_entity"}
        for block in detail["context_blocks"]
    )


def test_athena_chat_keeps_model_content_when_trace_attach_fails(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    monkeypatch.setattr(
        dialogs,
        "attach_trace_response",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("trace attach failed")),
    )
    project, _ = _seed_project(db_session, with_profile=True)

    response = client.post(
        f"/api/v1/projects/{project.id}/athena/dialog/chat",
        json={"project_id": project.id, "text": "请分析当前世界模型。"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == _FakeAiResult.content
    assert payload["trace_id"] is None

    assistant_message = (
        db_session.query(DialogMessage)
        .filter(DialogMessage.role == "assistant")
        .order_by(DialogMessage.created_at.desc())
        .first()
    )
    assert assistant_message is not None
    assert assistant_message.content == _FakeAiResult.content
