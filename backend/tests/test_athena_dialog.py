import pytest

from app.api import dialogs
from app.core.context_injection import (
    build_athena_world_context,
    build_athena_world_context_blocks,
    build_hermes_world_context,
    build_hermes_world_context_blocks,
)
from app.core.athena_longform import build_chapter_context_package
from app.models import (
    AIModelCallTrace,
    ChapterContent,
    Dialog,
    DialogMessage,
    GenreProfile,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldCharacter,
    WorldEvent,
    WorldFactClaim,
    WorldRelation,
    WorldRule,
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


def test_athena_chat_negated_update_wording_still_uses_ai_trace(client, db_session, monkeypatch):
    _enable_fake_ai(monkeypatch)
    project, _ = _seed_project(db_session)

    response = client.post(
        f"/api/v1/projects/{project.id}/athena/dialog/chat",
        json={
            "project_id": project.id,
            "text": "请先不要写入世界模型，只规划10章故事的世界规则。",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "世界模型已更新。"
    assert payload["trace_id"]
    assert payload["refresh_targets"] == []
    assert db_session.query(AIModelCallTrace).count() == 1
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


def test_world_context_assembler_is_shared_by_dialog_and_chapter_context(db_session):
    from app.core.world_context_assembler import WorldContextAssembler

    project, profile_version = _seed_project(db_session, with_profile=True)
    chapter = ChapterContent(
        project_id=project.id,
        chapter_index=3,
        title="旧灯塔",
        content="林舟抵达旧灯塔。",
        status="draft",
    )
    fact = WorldFactClaim(
        project_id=project.id,
        project_profile_version_id=profile_version.id,
        profile_version=profile_version.version,
        claim_id="fact.linzhou.role.shared",
        chapter_index=2,
        intra_chapter_seq=1,
        subject_ref="character.linzhou",
        predicate="role",
        object_ref_or_value="雾港城守夜人",
        claim_layer="truth",
        claim_status="confirmed",
        authority_type="authoritative_structured",
        confidence=1.0,
        contract_version=profile_version.contract_version,
    )
    db_session.add_all([chapter, fact])
    db_session.commit()

    assembler = WorldContextAssembler(db_session, project.id)
    assembler_text = assembler.dialog_context_text("athena")
    dialog_text = build_athena_world_context(db_session, project.id)
    block_text = "\n".join(block["content"] for block in build_athena_world_context_blocks(db_session, project.id))
    chapter_package = build_chapter_context_package(db_session, project.id, 3)

    expected_fact = "character.linzhou.role = 雾港城守夜人"
    assert expected_fact in assembler_text
    assert expected_fact in dialog_text
    assert expected_fact in block_text
    assert expected_fact in chapter_package["prompt_context"]
    assert any(section["key"] == "facts" for section in chapter_package["sections"])


def test_chapter_context_exposes_retrieval_warning_when_retrieval_fails(db_session, monkeypatch):
    import app.core.athena_retrieval as athena_retrieval

    project, profile_version = _seed_project(db_session, with_profile=True)
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=2,
            title="旧灯塔",
            content="林舟抵达旧灯塔。",
            status="draft",
        )
    )
    db_session.commit()

    def raise_retrieval_error(*args, **kwargs):
        raise RuntimeError("retrieval index offline")

    monkeypatch.setattr(athena_retrieval, "build_chapter_retrieval_context", raise_retrieval_error)

    package = build_chapter_context_package(db_session, project.id, 2)

    warning_section = next(section for section in package["sections"] if section["key"] == "retrieval_warning")
    assert warning_section["items"][0]["code"] == "retrieval_context_failed"
    assert "检索证据暂不可用" in package["prompt_context"]
    assert profile_version.id == package["project_profile_version_id"]


def test_world_context_builders_use_current_world_model_field_names(db_session):
    project, profile_version = _seed_project(db_session, with_profile=True)
    db_session.add_all(
        [
            WorldCharacter(
                project_id=project.id,
                profile_version=profile_version.version,
                character_id="character.linzhou",
                canonical_id="character.linzhou",
                primary_alias="林舟",
                name="林舟",
                aliases=[],
                role_type="protagonist",
                identity_anchor="雾港城守夜人",
                contract_version=profile_version.contract_version,
            ),
            WorldRelation(
                project_id=project.id,
                profile_version=profile_version.version,
                relation_id="relation.linzhou-yunyao",
                source_entity_ref="character.linzhou",
                target_entity_ref="character.yunyao",
                relation_type="ally",
                directionality="directed",
                status="active",
                visibility_layer="public",
                contract_version=profile_version.contract_version,
            ),
            WorldRule(
                project_id=project.id,
                profile_version=profile_version.version,
                rule_id="rule.fog",
                canonical_id="rule.fog",
                primary_alias="雾港潮汐",
                name="雾港潮汐",
                rule_type="environment",
                statement="雾潮会吞噬未点灯的街区",
                contract_version=profile_version.contract_version,
            ),
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_version.id,
                profile_version=profile_version.version,
                event_id="event.fog.arrives",
                idempotency_key="event.fog.arrives",
                timeline_anchor_id="anchor.ch1",
                chapter_index=1,
                intra_chapter_seq=1,
                event_type="world_state_changed",
                primitive_payload={"summary": "雾潮抵达旧港"},
                truth_layer="truth",
                disclosure_layer="public",
                contract_version=profile_version.contract_version,
            ),
        ]
    )
    db_session.commit()

    athena_context = build_athena_world_context(db_session, project.id)
    hermes_context = build_hermes_world_context(db_session, project.id)
    athena_blocks = build_athena_world_context_blocks(db_session, project.id)
    hermes_blocks = build_hermes_world_context_blocks(db_session, project.id)

    assert "protagonist" in athena_context
    assert "character.linzhou → ally → character.yunyao" in athena_context
    assert "雾港潮汐：雾潮会吞噬未点灯的街区" in athena_context
    assert '{"summary": "雾潮抵达旧港"}' in athena_context
    assert "character.linzhou → ally → character.yunyao" in hermes_context
    assert any("character.linzhou → ally → character.yunyao" in block["content"] for block in athena_blocks)
    assert any("character.linzhou → ally → character.yunyao" in block["content"] for block in hermes_blocks)


def test_world_context_builders_do_not_leak_previous_profile_version(db_session):
    project, profile_v1 = _seed_project(db_session, with_profile=True)
    profile_v2 = ProjectProfileVersion(
        project_id=project.id,
        genre_profile_id=profile_v1.genre_profile_id,
        version=2,
        contract_version=profile_v1.contract_version,
        profile_payload={},
    )
    db_session.add(profile_v2)
    db_session.commit()

    db_session.add_all(
        [
            WorldCharacter(
                project_id=project.id,
                profile_version=profile_v1.version,
                character_id="character.old",
                canonical_id="character.old",
                primary_alias="旧角色",
                name="旧角色",
                aliases=[],
                role_type="deprecated",
                identity_anchor="旧档案",
                contract_version=profile_v1.contract_version,
            ),
            WorldCharacter(
                project_id=project.id,
                profile_version=profile_v2.version,
                character_id="character.new",
                canonical_id="character.new",
                primary_alias="新角色",
                name="新角色",
                aliases=[],
                role_type="lead",
                identity_anchor="新档案",
                contract_version=profile_v2.contract_version,
            ),
            WorldRelation(
                project_id=project.id,
                profile_version=profile_v1.version,
                relation_id="relation.old",
                source_entity_ref="character.old",
                target_entity_ref="character.leak",
                relation_type="leaked_relation",
                directionality="directed",
                status="active",
                visibility_layer="public",
                contract_version=profile_v1.contract_version,
            ),
            WorldRelation(
                project_id=project.id,
                profile_version=profile_v2.version,
                relation_id="relation.new",
                source_entity_ref="character.new",
                target_entity_ref="character.current",
                relation_type="current_relation",
                directionality="directed",
                status="active",
                visibility_layer="public",
                contract_version=profile_v2.contract_version,
            ),
            WorldRule(
                project_id=project.id,
                profile_version=profile_v1.version,
                rule_id="rule.old",
                canonical_id="rule.old",
                primary_alias="旧规则",
                name="旧规则",
                rule_type="setting",
                statement="旧规则不应出现",
                contract_version=profile_v1.contract_version,
            ),
            WorldRule(
                project_id=project.id,
                profile_version=profile_v2.version,
                rule_id="rule.new",
                canonical_id="rule.new",
                primary_alias="新规则",
                name="新规则",
                rule_type="setting",
                statement="新规则应出现",
                contract_version=profile_v2.contract_version,
            ),
            WorldFactClaim(
                project_id=project.id,
                project_profile_version_id=profile_v1.id,
                profile_version=profile_v1.version,
                claim_id="fact.old",
                chapter_index=1,
                intra_chapter_seq=1,
                subject_ref="character.old",
                predicate="status",
                object_ref_or_value="旧事实不应出现",
                claim_layer="truth",
                claim_status="confirmed",
                authority_type="authoritative_structured",
                confidence=1.0,
                contract_version=profile_v1.contract_version,
            ),
            WorldFactClaim(
                project_id=project.id,
                project_profile_version_id=profile_v2.id,
                profile_version=profile_v2.version,
                claim_id="fact.new",
                chapter_index=1,
                intra_chapter_seq=1,
                subject_ref="character.new",
                predicate="status",
                object_ref_or_value={"value": "新事实应出现"},
                claim_layer="truth",
                claim_status="confirmed",
                authority_type="authoritative_structured",
                confidence=1.0,
                contract_version=profile_v2.contract_version,
            ),
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_v1.id,
                profile_version=profile_v1.version,
                event_id="event.old",
                idempotency_key="event.old",
                timeline_anchor_id="anchor.old",
                chapter_index=1,
                intra_chapter_seq=1,
                event_type="old_event",
                primitive_payload={"summary": "旧事件不应出现"},
                truth_layer="truth",
                disclosure_layer="public",
                contract_version=profile_v1.contract_version,
            ),
            WorldEvent(
                project_id=project.id,
                project_profile_version_id=profile_v2.id,
                profile_version=profile_v2.version,
                event_id="event.new",
                idempotency_key="event.new",
                timeline_anchor_id="anchor.new",
                chapter_index=1,
                intra_chapter_seq=1,
                event_type="new_event",
                primitive_payload={"summary": "新事件应出现"},
                truth_layer="truth",
                disclosure_layer="public",
                contract_version=profile_v2.contract_version,
            ),
        ]
    )
    db_session.commit()

    outputs = [
        build_athena_world_context(db_session, project.id),
        build_hermes_world_context(db_session, project.id),
        "\n".join(block["content"] for block in build_athena_world_context_blocks(db_session, project.id)),
        "\n".join(block["content"] for block in build_hermes_world_context_blocks(db_session, project.id)),
    ]

    for output in outputs:
        assert "新角色" in output
        assert "character.new.status = {\"value\": \"新事实应出现\"}" in output
        assert "character.new → current_relation → character.current" in output
        assert "旧角色" not in output
        assert "旧事实不应出现" not in output
        assert "leaked_relation" not in output
    athena_outputs = "\n".join(outputs[0::2])
    assert "新规则：新规则应出现" in athena_outputs
    assert "new_event {\"summary\": \"新事件应出现\"}" in athena_outputs
    assert "旧规则不应出现" not in athena_outputs
    assert "旧事件不应出现" not in athena_outputs


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


def test_athena_chat_payload_includes_manuscript_progress_context(db_session):
    project, _ = _seed_project(db_session, with_profile=True)
    project.target_chapter_count = 20
    project.current_word_count = 78127
    project.current_phase = "content"
    dialog = Dialog(project_id=project.id, dialog_type="athena")
    db_session.add(dialog)
    for index in range(1, 21):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=index,
                title=f"第{index}章标题",
                content=f"第{index}章正文内容。" * 20,
                word_count=3000 + index,
                status="draft",
            )
        )
    db_session.commit()

    payload = dialogs._build_chat_call_payload(
        db_session,
        dialog.id,
        project,
        dialogs._build_diagnosis(db_session, project.id),
        dialog_type="athena",
    )

    manuscript_block = next(
        block for block in payload["context_blocks"]
        if block["kind"] == "manuscript_summary"
    )
    assert "已生成章节：20 / 目标 20" in manuscript_block["content"]
    assert "当前总字数：78127" in manuscript_block["content"]
    assert "第20章《第20章标题》" in manuscript_block["content"]
    assert "已生成章节：20 / 目标 20" in payload["messages"][0]["content"]
    assert "正文进度是章节数量、总字数和最近章节的权威来源" in payload["messages"][0]["content"]
    assert manuscript_block["sources"][0]["source_type"] == "ChapterContent"


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
