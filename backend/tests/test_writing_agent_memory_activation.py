from app.models import ChapterContent, LongformMemory, Project, RetrievalDocument, Storyline
from app.services.writing_agent.memory_activation import build_memory_activation_plan


def test_memory_activation_selects_prior_memory_and_foreshadowing_without_future_leak(db_session):
    project = Project(
        name="Memory Activation",
        genre="悬疑科幻",
        style="冷峻、短句、强悬念",
        style_config={
            "tone": "冷峻",
            "pov": "第三人称限知",
            "knowledge_base_candidates": [
                {
                    "id": "candidate-active-pattern",
                    "memory_type": "writing_pattern",
                    "title": "章末钩子",
                    "summary": "每章结尾保留一个可追踪的实物线索。",
                    "confidence": 0.82,
                    "status": "active",
                    "source_refs": ["chapter_content:2"],
                    "tags": ["post-chapter-capture"],
                    "updated_at": "2026-05-01T10:00:00Z",
                },
                {
                    "id": "candidate-low-confidence",
                    "memory_type": "writing_pattern",
                    "title": "低置信经验",
                    "summary": "这条候选还不能进入写前激活。",
                    "confidence": 0.45,
                    "status": "candidate",
                    "source_refs": ["chapter_content:2"],
                },
                {
                    "id": "candidate-muted",
                    "memory_type": "writing_pattern",
                    "title": "静默经验",
                    "summary": "静默候选不能进入写前激活。",
                    "confidence": 0.95,
                    "status": "muted",
                    "source_refs": ["chapter_content:2"],
                },
            ],
        },
    )
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=1,
                title="雾港来信",
                content="林深在旧灯塔收到空白信，信纸遇水显出黑潮门坐标。",
                word_count=30,
                status="generated",
            ),
            ChapterContent(
                project_id=project.id,
                chapter_index=2,
                title="黑市回声",
                content="苏晚晴在黑市确认雾晶会吞掉人的短期记忆。",
                word_count=25,
                status="generated",
            ),
            ChapterContent(
                project_id=project.id,
                chapter_index=4,
                title="未来章节",
                content="未来章节里才会揭示潮下车站。",
                word_count=20,
                status="generated",
            ),
        ]
    )
    chapter_1_memory = LongformMemory(
        project_id=project.id,
        memory_type="chapter",
        scope_key="chapter:1",
        start_chapter_index=1,
        end_chapter_index=1,
        title="雾港来信",
        summary="空白信遇水显出黑潮门坐标。",
        status="current",
    )
    chapter_2_memory = LongformMemory(
        project_id=project.id,
        memory_type="chapter",
        scope_key="chapter:2",
        start_chapter_index=2,
        end_chapter_index=2,
        title="黑市回声",
        summary="雾晶会吞掉短期记忆。",
        status="current",
    )
    chapter_4_memory = LongformMemory(
        project_id=project.id,
        memory_type="chapter",
        scope_key="chapter:4",
        start_chapter_index=4,
        end_chapter_index=4,
        title="未来章节",
        summary="潮下车站是未来才揭示的地点。",
        status="current",
    )
    db_session.add_all(
        [
            LongformMemory(
                project_id=project.id,
                memory_type="global",
                scope_key="global",
                start_chapter_index=1,
                end_chapter_index=2,
                title="全书记忆",
                summary="已建立旧灯塔、空白信、雾晶记忆代价。",
                status="current",
            ),
            LongformMemory(
                project_id=project.id,
                memory_type="arc",
                scope_key="arc:1-2",
                start_chapter_index=1,
                end_chapter_index=2,
                title="第1-2章",
                summary="林深追查空白信，苏晚晴发现雾晶副作用。",
                status="current",
            ),
            chapter_1_memory,
            chapter_2_memory,
            chapter_4_memory,
        ]
    )
    db_session.flush()
    db_session.add_all(
        [
            _retrieval_doc(project.id, chapter_1_memory, 1),
            _retrieval_doc(project.id, chapter_2_memory, 2),
            _retrieval_doc(project.id, chapter_4_memory, 4),
        ]
    )
    db_session.add(
        Storyline(
            project_id=project.id,
            status="generated",
            plotlines=[],
            foreshadowing=[
                {
                    "title": "空白信来源",
                    "summary": "空白信来自黑潮门内部。",
                    "introduced_chapter": 1,
                    "expected_resolution_chapter": 5,
                    "status": "open",
                },
                {
                    "title": "潮下车站",
                    "summary": "未来地点，不应提前泄漏。",
                    "introduced_chapter": 4,
                    "expected_resolution_chapter": 8,
                    "status": "open",
                },
            ],
        )
    )
    db_session.commit()

    output = build_memory_activation_plan(db_session, project.id, chapter_index=3, query="生成第3章")

    assert output["status"] == "ready"
    assert output["chapter_index"] == 3
    assert output["coverage"]["memory_coverage_debt"]["status"] == "ready"
    longform_titles = [item["title"] for item in output["activation"]["longform"]]
    assert "雾港来信" in longform_titles
    assert "黑市回声" in longform_titles
    assert "未来章节" not in longform_titles
    foreshadow_titles = [item["title"] for item in output["activation"]["foreshadowing"]]
    assert foreshadow_titles == ["空白信来源"]
    knowledge_titles = [item["title"] for item in output["activation"]["knowledge_base"]]
    assert knowledge_titles == ["章末钩子"]
    assert output["coverage"]["activated_counts"]["knowledge_base"] == 1
    assert "空白信" in output["prompt_block"]
    assert "雾晶" in output["prompt_block"]
    assert "章末钩子" in output["prompt_block"]
    assert "低置信经验" not in output["prompt_block"]
    assert "静默经验" not in output["prompt_block"]
    assert "潮下车站" not in output["prompt_block"]
    assert output["memory_provenance"]["status"] == "available"
    source_refs = {source["source_ref"] for source in output["memory_provenance"]["sources"]}
    assert "knowledge_base_candidate:candidate-active-pattern" in source_refs
    assert output["memory_provenance"]["windows"]["knowledge_base"] == {
        "total": 1,
        "returned": 1,
        "limit": 4,
        "has_more": False,
    }
    assert output["trace"]["runtime_behavior_changed"] is False


def test_memory_activation_includes_relevant_memory_tree_drilldown_without_future_leak(db_session):
    project = Project(name="Memory Tree Activation")
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            ChapterContent(
                project_id=project.id,
                chapter_index=1,
                title="雾港来信",
                content="林深在旧灯塔收到空白信。",
                word_count=20,
                status="generated",
            ),
            ChapterContent(
                project_id=project.id,
                chapter_index=2,
                title="灯塔回声",
                content="顾衍追查旧回声。",
                word_count=20,
                status="generated",
            ),
            ChapterContent(
                project_id=project.id,
                chapter_index=4,
                title="未来灯塔真相",
                content="未来才揭示灯塔旧回声来自潮下车站。",
                word_count=20,
                status="generated",
            ),
        ]
    )
    db_session.add_all(
        [
            LongformMemory(
                project_id=project.id,
                memory_type="chapter",
                scope_key="chapter:2",
                start_chapter_index=2,
                end_chapter_index=2,
                title="灯塔回声",
                summary="顾衍确认旧回声与灯塔地下室有关。",
                status="current",
            ),
            LongformMemory(
                project_id=project.id,
                memory_type="chapter",
                scope_key="chapter:4",
                start_chapter_index=4,
                end_chapter_index=4,
                title="未来灯塔真相",
                summary="潮下车站是未来才揭示的地点。",
                status="current",
            ),
        ]
    )
    db_session.commit()

    output = build_memory_activation_plan(db_session, project.id, chapter_index=3, query="灯塔旧回声")

    memory_tree = output["activation"]["memory_tree"]
    assert [item["node_id"] for item in memory_tree] == ["chapter:2"]
    assert memory_tree[0]["kind"] == "memory_tree_node"
    assert memory_tree[0]["relevance"]["score"] > 0.75
    assert "semantic_token_overlap" in memory_tree[0]["relevance"]["match_reasons"]
    assert output["coverage"]["activated_counts"]["memory_tree"] == 1
    assert "灯塔回声" in output["prompt_block"]
    assert "未来灯塔真相" not in output["prompt_block"]
    assert output["memory_provenance"]["windows"]["memory_tree"] == {
        "total": 1,
        "returned": 1,
        "limit": 3,
        "has_more": False,
    }
    source_refs = {source["source_ref"] for source in output["memory_provenance"]["sources"]}
    assert "memory_tree:chapter:2" in source_refs
    assert "memory_tree:chapter:4" not in source_refs


def test_memory_activation_reports_coverage_debt_for_missing_memory(db_session):
    project = Project(name="Memory Debt")
    db_session.add(project)
    db_session.flush()
    db_session.add(
        ChapterContent(
            project_id=project.id,
            chapter_index=1,
            title="已生成但未沉淀",
            content="这一章还没有长篇记忆。",
            word_count=12,
            status="generated",
        )
    )
    db_session.commit()

    output = build_memory_activation_plan(db_session, project.id, chapter_index=2)

    assert output["status"] == "degraded"
    debt = output["coverage"]["memory_coverage_debt"]
    assert debt["status"] == "degraded"
    assert debt["missing_memory_count"] == 1
    assert output["recommended_next_tools"] == ["prepare_repair_longform_maintenance", "inspect_agent_memory_route"]
    assert any(risk["code"] == "memory_coverage_debt" for risk in output["risks"])


def _retrieval_doc(project_id, memory, chapter_index):
    return RetrievalDocument(
        project_id=project_id,
        source_type="longform_memory",
        source_id=memory.id,
        source_ref=f"memory:{memory.scope_key}",
        title=memory.title,
        chapter_index=chapter_index,
        content_hash=f"hash-{memory.scope_key}",
    )
