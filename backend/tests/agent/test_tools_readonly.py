import pytest

from app.agent.tooling import ToolContext
from app.models import (
    ChapterContent,
    GenreProfile,
    Outline,
    Project,
    ProjectProfileVersion,
    Setup,
    WorldCharacter,
)
from app.tools.registry import build_default_registry


@pytest.fixture
def project(db_session):
    p = Project(name="灯塔旧回声", genre="奇幻", target_chapter_count=100)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


@pytest.fixture
def ctx(db_session, project):
    return ToolContext(project_id=project.id, session_id="s1", db=db_session)


@pytest.fixture
def registry():
    return build_default_registry()


def add_chapter(db, project_id, index, title="", content="", status="completed"):
    ch = ChapterContent(
        project_id=project_id, chapter_index=index, title=title,
        content=content, word_count=len(content), status=status,
    )
    db.add(ch)
    db.commit()
    return ch


@pytest.mark.asyncio
async def test_get_project_state(db_session, project, ctx, registry):
    db_session.add(Setup(project_id=project.id, status="completed"))
    db_session.add(Outline(project_id=project.id, status="completed", total_chapters=100))
    add_chapter(db_session, project.id, 1, title="第一章")

    result = await registry.execute("get_project_state", {}, ctx)
    assert not result.is_error
    assert result.data["project"]["name"] == "灯塔旧回声"
    assert result.data["setup_status"] == "completed"
    assert result.data["outline_status"] == "completed"
    assert result.data["chapter_count"] == 1


@pytest.mark.asyncio
async def test_get_project_state_missing_project(db_session, registry):
    ctx = ToolContext(project_id="nonexistent", db=db_session)
    result = await registry.execute("get_project_state", {}, ctx)
    assert result.is_error
    assert "项目" in result.error


@pytest.mark.asyncio
async def test_list_chapters_ordered_with_window(db_session, project, ctx, registry):
    for i in (3, 1, 2):
        add_chapter(db_session, project.id, i, title=f"第{i}章", content="x" * i)

    result = await registry.execute("list_chapters", {}, ctx)
    assert not result.is_error
    assert [c["chapter_index"] for c in result.data["chapters"]] == [1, 2, 3]
    assert result.data["total"] == 3

    windowed = await registry.execute("list_chapters", {"start": 2, "limit": 1}, ctx)
    assert [c["chapter_index"] for c in windowed.data["chapters"]] == [2]


@pytest.mark.asyncio
async def test_read_chapter(db_session, project, ctx, registry):
    add_chapter(db_session, project.id, 5, title="灯塔", content="海雾散去。")
    result = await registry.execute("read_chapter", {"chapter_index": 5}, ctx)
    assert not result.is_error
    assert result.data["title"] == "灯塔"
    assert result.data["content"] == "海雾散去。"


@pytest.mark.asyncio
async def test_read_chapter_not_found_suggests_range(db_session, project, ctx, registry):
    add_chapter(db_session, project.id, 1)
    result = await registry.execute("read_chapter", {"chapter_index": 99}, ctx)
    assert result.is_error
    assert "99" in result.error
    assert "list_chapters" in result.error or "1" in result.error


@pytest.mark.asyncio
async def test_query_world_characters_by_name(db_session, project, ctx, registry):
    genre = GenreProfile(
        canonical_id="test-genre", display_name="测试", contract_version="world.contract.v1",
    )
    db_session.add(genre)
    db_session.commit()
    profile = ProjectProfileVersion(
        project_id=project.id, genre_profile_id=genre.id, version=1,
        contract_version="world.contract.v1", profile_payload={},
    )
    db_session.add(profile)
    db_session.commit()
    db_session.add(WorldCharacter(
        project_id=project.id, profile_version=1,
        character_id="c1", canonical_id="char:linsi", name="林思",
        aliases=["小林"], role_type="protagonist", identity_anchor="灯塔守望者",
        core_traits=["坚韧"], contract_version="world.contract.v1",
    ))
    db_session.commit()

    result = await registry.execute("query_world", {"query": "林思"}, ctx)
    assert not result.is_error
    chars = result.data["characters"]
    assert len(chars) == 1
    assert chars[0]["name"] == "林思"
    assert chars[0]["identity_anchor"] == "灯塔守望者"

    by_alias = await registry.execute("query_world", {"query": "小林"}, ctx)
    assert len(by_alias.data["characters"]) == 1


@pytest.mark.asyncio
async def test_query_world_no_profile_returns_guidance(db_session, project, ctx, registry):
    result = await registry.execute("query_world", {"query": "林思"}, ctx)
    assert not result.is_error
    assert result.data["characters"] == []


@pytest.mark.asyncio
async def test_query_world_falls_back_to_update_setup_data(db_session, project, ctx, registry):
    """无 world profile 时，query_world 应回退读取 update_setup 写入的 Setups 表。"""
    db_session.add(Setup(
        project_id=project.id,
        world_building={"城市": "雾镇"},
        characters=[{"name": "沈砚", "role": "主角", "aliases": ["砚哥"]}],
        core_concept={"主题": "记忆与真相"},
        status="generated",
    ))
    db_session.commit()

    result = await registry.execute("query_world", {"query": ""}, ctx)
    assert not result.is_error
    assert len(result.data["characters"]) == 1
    assert result.data["characters"][0]["name"] == "沈砚"
    assert "update_setup" in result.data["note"]

    by_alias = await registry.execute("query_world", {"query": "砚哥"}, ctx)
    assert len(by_alias.data["characters"]) == 1


@pytest.mark.asyncio
async def test_search_text_wraps_retrieval(db_session, project, ctx, registry):
    add_chapter(db_session, project.id, 1, title="第一章", content="林思在灯塔上点燃了旧回声。")
    from app.core.athena_retrieval import reindex_project_retrieval
    reindex_project_retrieval(db_session, project.id)

    result = await registry.execute("search_text", {"query": "灯塔"}, ctx)
    assert not result.is_error
    assert result.data["total"] >= 1
    assert any("灯塔" in item["excerpt"] for item in result.data["items"])


@pytest.mark.asyncio
async def test_all_first_batch_tools_are_read_permission(registry):
    from app.agent.tooling import PermissionLevel
    for name in ("get_project_state", "list_chapters", "read_chapter", "query_world", "search_text"):
        assert registry.get(name).permission == PermissionLevel.READ, name
