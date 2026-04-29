from app.api import dialogs
from app.models import (
    AIModelCallTrace,
    Dialog,
    DialogMessage,
    GenreProfile,
    Project,
    ProjectProfileVersion,
    WorldCharacter,
    WorldFactClaim,
)


class _FakeAiResult:
    content = "收到，我会基于当前项目状态回答。"
    prompt_tokens = 101
    completion_tokens = 17


async def _fake_complete(*args, **kwargs):
    return _FakeAiResult()


def _enable_fake_ai(monkeypatch):
    monkeypatch.setattr(dialogs, "load_api_key", lambda: True)
    monkeypatch.setattr(dialogs.ai_service, "complete", _fake_complete)


def _seed_project_with_world(db_session, *, dialog_type: str = "hermes"):
    project = Project(
        name="雾港纪事",
        genre="东方奇幻悬疑",
        description="潮汐吞没记忆的港城。",
        current_phase="content",
        status="writing",
        current_word_count=1200,
        target_chapter_count=12,
        target_word_count=60000,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    genre_profile = GenreProfile(
        canonical_id=f"prompt-dialog-{project.id}",
        display_name="通用",
        contract_version="world.contract.v1",
    )
    db_session.add(genre_profile)
    db_session.commit()

    profile = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=genre_profile.id,
        version=3,
        contract_version="world.contract.v1",
        profile_payload={},
    )
    db_session.add(profile)
    db_session.commit()

    db_session.add_all(
        [
            WorldCharacter(
                project_id=project.id,
                profile_version=profile.version,
                character_id="character.linzhou",
                canonical_id="character.linzhou",
                primary_alias="林舟",
                name="林舟",
                aliases=["守夜人"],
                role_type="protagonist",
                identity_anchor="雾港城守夜人",
                contract_version=profile.contract_version,
            ),
            WorldFactClaim(
                project_id=project.id,
                project_profile_version_id=profile.id,
                profile_version=profile.version,
                claim_id="fact.linzhou.role",
                chapter_index=1,
                subject_ref="character.linzhou",
                predicate="role",
                object_ref_or_value="雾港城守夜人",
                claim_layer="truth",
                claim_status="confirmed",
                authority_type="authoritative_structured",
                confidence=1.0,
                contract_version=profile.contract_version,
            ),
        ]
    )
    db_session.commit()

    dialog = Dialog(project_id=project.id, dialog_type=dialog_type)
    db_session.add(dialog)
    db_session.commit()
    db_session.refresh(dialog)

    return project, profile, dialog


def test_hermes_chat_payload_uses_prompt_orchestration_and_trace_context(db_session):
    project, _profile, dialog = _seed_project_with_world(db_session, dialog_type="hermes")
    db_session.add_all(
        [
            DialogMessage(dialog_id=dialog.id, role="user", content="上一轮问题"),
            DialogMessage(dialog_id=dialog.id, role="system", content="已生成第一章"),
        ]
    )
    db_session.commit()

    diagnosis = dialogs._build_diagnosis(db_session, project.id)
    payload = dialogs._build_chat_call_payload(
        db_session,
        dialog.id,
        project,
        diagnosis,
        dialog_type="hermes",
    )

    assert payload["trace_metadata"]["prompt_id"] == "dialog.hermes"
    assert payload["trace_metadata"]["dialog_type"] == "hermes"
    system_message = payload["messages"][0]
    assert system_message["role"] == "system"
    assert "当前阶段：正文阶段" in system_message["content"]
    assert "当前状态：正文写作中" in system_message["content"]
    assert "主要角色：林舟" in system_message["content"]
    assert {block["kind"] for block in payload["context_blocks"]} >= {
        "world_entity",
        "world_fact",
        "dialog_history",
    }
    history_block = next(block for block in payload["context_blocks"] if block["kind"] == "dialog_history")
    assert "user: 上一轮问题" in history_block["content"]
    assert "assistant: [系统消息] 已生成第一章" in history_block["content"]
    assert payload["messages"][-1] == {"role": "assistant", "content": "[系统消息] 已生成第一章"}


def test_athena_chat_payload_uses_prompt_orchestration_and_profile_context(db_session):
    project, profile, dialog = _seed_project_with_world(db_session, dialog_type="athena")
    db_session.add(DialogMessage(dialog_id=dialog.id, role="user", content="林舟的身份是什么？"))
    db_session.commit()

    diagnosis = dialogs._build_diagnosis(db_session, project.id)
    payload = dialogs._build_chat_call_payload(
        db_session,
        dialog.id,
        project,
        diagnosis,
        dialog_type="athena",
    )

    assert payload["trace_metadata"]["prompt_id"] == "dialog.athena"
    assert payload["trace_metadata"]["dialog_type"] == "athena"
    assert f"世界档案版本：{profile.version}" in payload["messages"][0]["content"]
    assert "林舟" in payload["messages"][0]["content"]
    assert {block["kind"] for block in payload["context_blocks"]} >= {
        "world_entity",
        "world_fact",
        "dialog_history",
    }
    history_block = next(block for block in payload["context_blocks"] if block["kind"] == "dialog_history")
    assert "user: 林舟的身份是什么？" in history_block["content"]


def test_hermes_chat_api_trace_detail_records_prompt_metadata(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project, _profile, _dialog = _seed_project_with_world(db_session, dialog_type="hermes")

    response = client.post(
        "/api/v1/dialog/chat",
        json={"project_id": project.id, "text": "帮我判断下一步。"},
    )

    assert response.status_code == 200
    trace_id = response.json()["trace_id"]
    assert trace_id
    detail_response = client.get(f"/api/v1/projects/{project.id}/model-call-traces/{trace_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["trace_metadata"]["prompt_id"] == "dialog.hermes"
    assert detail["trace_metadata"]["dialog_type"] == "hermes"
    assert any(block["kind"] == "dialog_history" for block in detail["context_blocks"])


def test_safe_chat_trace_keeps_prompt_metadata_and_dialog_type(db_session):
    project, _profile, dialog = _seed_project_with_world(db_session, dialog_type="hermes")
    diagnosis = dialogs._build_diagnosis(db_session, project.id)
    payload = dialogs._build_chat_call_payload(
        db_session,
        dialog.id,
        project,
        diagnosis,
        dialog_type="hermes",
    )

    trace = dialogs._safe_create_chat_trace(
        db_session,
        project_id=project.id,
        trace_type="hermes_chat",
        messages=payload["messages"],
        context_blocks=payload["context_blocks"],
        model="deepseek-chat",
        temperature=0.7,
        max_tokens=900,
        dialog_id=dialog.id,
        request_message_id=None,
        trace_metadata=payload["trace_metadata"],
    )

    assert trace is not None
    stored = db_session.query(AIModelCallTrace).filter(AIModelCallTrace.id == trace.id).one()
    assert stored.trace_metadata["prompt_id"] == "dialog.hermes"
    assert stored.trace_metadata["dialog_type"] == "hermes"
