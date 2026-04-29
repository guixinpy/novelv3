from app.api import chapters
from app.models import ChapterContent, Outline, Project, Setup


def _project(db_session, **kwargs) -> Project:
    project = Project(
        id=kwargs.pop("id", "chapter-prompt-project"),
        name=kwargs.pop("name", "霜灯塔"),
        genre=kwargs.pop("genre", "仙侠悬疑"),
        language=kwargs.pop("language", "zh-CN"),
        style_config=kwargs.pop("style_config", {"description_density": 4}),
        **kwargs,
    )
    db_session.add(project)
    db_session.commit()
    return project


def _setup(db_session, project_id: str) -> Setup:
    setup = Setup(
        project_id=project_id,
        world_building={"city": "雾城", "rule": "潮汐会吞没记忆"},
        characters=[{"name": "林舟", "role": "守塔人"}],
        core_concept={"hook": "霜灯塔只在失忆者梦中点亮"},
    )
    db_session.add(setup)
    db_session.commit()
    return setup


def test_chapter_payload_uses_prompt_orchestration_and_injects_context(monkeypatch, db_session):
    project = _project(db_session)
    setup = _setup(db_session, project.id)
    db_session.add(
        Outline(
            project_id=project.id,
            total_chapters=3,
            chapters=[
                {"chapter_index": 3, "title": "第三夜", "summary": "林舟进入霜灯塔", "scenes": ["塔顶"], "characters": ["林舟"]},
            ],
            plotlines=[],
            foreshadowing=[],
        )
    )
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=2,
            title="第二夜",
            content="第二章已经揭示潮汐会偷走姓名。",
            status="generated",
        )
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.prompting.providers.athena.build_chapter_context_package",
        lambda **kwargs: {
            "chapter_index": kwargs["chapter_index"],
            "profile_version": 7,
            "project_profile_version_id": "profile-7",
            "sections": [{"key": "retrieval", "title": "检索证据", "items": [{"title": "旧证据"}]}],
            "prompt_context": "【世界模型】Profile v7\n霜灯塔规则\n【检索证据】\n- 世界事实 旧证据：林舟害怕灯光",
        },
    )
    monkeypatch.setattr(
        "app.prompting.providers.retrieval.build_chapter_retrieval_context",
        lambda **kwargs: {
            "section": {"key": "retrieval", "title": "检索证据", "items": [{"title": "重复证据"}]},
            "prompt_lines": ["【检索证据】", "- 世界事实 重复证据：不应重复注入"],
        },
    )

    payload = chapters._build_chapter_call_payload(
        db_session,
        project,
        setup,
        3,
        "每章约1800-2200字，并强化灯塔压迫感",
    )

    message = payload["messages"][0]["content"]
    assert "创作第 3 章正文" in message
    assert "创作第 1 章正文" not in message
    assert "雾城" in message
    assert "林舟" in message
    assert "第三夜：林舟进入霜灯塔" in message
    assert "第二章已经揭示潮汐会偷走姓名" in message
    assert "霜灯塔规则" in message
    assert "旧证据" in message
    assert "重复证据" not in message
    assert "增加环境描写和感官细节" in message
    assert "【参考示例】" in message
    assert "青云宗" in message
    assert "正文长度控制在1800-2200字" in message

    metadata = payload["trace_metadata"]
    assert metadata["prompt_id"] == "chapter.generate"
    assert metadata["template_name"] == "generate_chapter"
    assert metadata["template_hash"].startswith("sha256:")
    assert metadata["budget"]["max_context_chars"] == 24000
    assert metadata["budget"]["included_blocks"] >= 1

    blocks_by_key = {block["key"]: block for block in payload["context_blocks"]}
    assert "generate_chapter_template" in blocks_by_key
    assert "athena_world_context" in blocks_by_key
    assert blocks_by_key["athena_world_context"]["sources"][0]["metadata"]["profile_version"] == 7
    assert "style_rule" in blocks_by_key
    assert "few_shot_examples" in blocks_by_key
    assert payload["max_tokens"] == 3000


def test_chapter_payload_injects_retrieval_when_athena_context_lacks_it(monkeypatch, db_session):
    project = _project(db_session, id="chapter-prompt-retrieval", style_config=None)
    setup = _setup(db_session, project.id)
    monkeypatch.setattr(
        "app.prompting.providers.athena.build_chapter_context_package",
        lambda **kwargs: {
            "chapter_index": kwargs["chapter_index"],
            "profile_version": 2,
            "project_profile_version_id": "profile-2",
            "sections": [],
            "prompt_context": "【世界模型】Profile v2\n只有世界模型，没有检索证据",
        },
    )
    monkeypatch.setattr(
        "app.prompting.providers.retrieval.build_chapter_retrieval_context",
        lambda **kwargs: {
            "section": {"key": "retrieval", "title": "检索证据", "items": [{"title": "章节证据"}]},
            "prompt_lines": ["【检索证据】", "- 章节 第1章 章节证据：海潮倒灌进旧城"],
        },
    )

    payload = chapters._build_chapter_call_payload(db_session, project, setup, 2, "")

    message = payload["messages"][0]["content"]
    assert "章节证据" in message
    assert message.count("【检索证据】") == 1
    assert any(block["key"] == "retrieval_evidence" for block in payload["context_blocks"])


def test_safe_create_chapter_trace_persists_prompt_metadata(db_session):
    project = _project(db_session, id="chapter-prompt-trace", style_config=None)

    trace = chapters._safe_create_chapter_trace(
        db_session,
        project=project,
        chapter_index=4,
        payload={
            "messages": [{"role": "user", "content": "生成第四章"}],
            "context_blocks": [],
            "max_tokens": 1200,
            "trace_metadata": {
                "prompt_id": "chapter.generate",
                "prompt_version": "1",
                "template_name": "generate_chapter",
                "template_hash": "sha256:test",
                "budget": {"max_context_chars": 24000, "included_blocks": 0, "omitted_blocks": 0},
            },
        },
    )

    assert trace is not None
    assert trace.trace_metadata["prompt_id"] == "chapter.generate"
    assert trace.trace_metadata["budget"]["max_context_chars"] == 24000
