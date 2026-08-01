import pytest

from app.agent.tooling import (
    PermissionLevel,
    ToolContext,
    ToolDefinition,
    ToolRegistry,
    ToolResult,
    tool,
)


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @tool(
        registry=registry,
        name="read_chapter",
        description="读取指定章节",
        permission="read",
        parameters={
            "type": "object",
            "properties": {"chapter_index": {"type": "integer"}},
            "required": ["chapter_index"],
        },
    )
    async def read_chapter(ctx: ToolContext, chapter_index: int) -> ToolResult:
        return ToolResult.ok({"index": chapter_index, "content": "正文"})

    @tool(
        registry=registry,
        name="write_chapter",
        description="写入章节",
        permission="write",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
    )
    async def write_chapter(ctx: ToolContext, text: str = "") -> ToolResult:
        return ToolResult.ok({"written": len(text)})

    return registry


def test_registration_and_specs():
    registry = make_registry()
    assert set(registry.names()) == {"read_chapter", "write_chapter"}
    specs = registry.to_specs()
    spec = next(s for s in specs if s.name == "read_chapter")
    assert spec.description == "读取指定章节"
    assert spec.parameters["required"] == ["chapter_index"]


def test_duplicate_name_rejected():
    registry = make_registry()
    with pytest.raises(ValueError, match="read_chapter"):

        @tool(registry=registry, name="read_chapter", description="dup", permission="read",
              parameters={"type": "object", "properties": {}})
        async def dup(ctx: ToolContext) -> ToolResult:
            return ToolResult.ok({})


def test_permission_levels():
    registry = make_registry()
    assert registry.get("read_chapter").permission == PermissionLevel.READ
    assert registry.get("write_chapter").permission == PermissionLevel.WRITE


@pytest.mark.asyncio
async def test_execute_happy_path():
    registry = make_registry()
    ctx = ToolContext(project_id=1)
    result = await registry.execute("read_chapter", {"chapter_index": 3}, ctx)
    assert result.is_error is False
    assert result.data == {"index": 3, "content": "正文"}


@pytest.mark.asyncio
async def test_unknown_tool_returns_model_actionable_error():
    registry = make_registry()
    result = await registry.execute("does_not_exist", {}, ToolContext(project_id=1))
    assert result.is_error
    assert "does_not_exist" in result.error
    # 错误信息要可恢复：告诉模型有哪些工具可用
    assert "read_chapter" in result.error


@pytest.mark.asyncio
async def test_execute_error_rolls_back_db_session():
    """工具异常后必须 rollback session，否则同请求后续工具全部失败。"""
    registry = ToolRegistry()

    class FakeDb:
        def __init__(self) -> None:
            self.rolled_back = False

        def rollback(self) -> None:
            self.rolled_back = True

    @tool(registry=registry, name="boom", description="抛错", permission="read",
          parameters={"type": "object", "properties": {}})
    async def boom(ctx: ToolContext) -> ToolResult:
        raise RuntimeError("db exploded")

    db = FakeDb()
    result = await registry.execute("boom", {}, ToolContext(project_id=1, db=db))
    assert result.is_error
    assert "db exploded" in result.error
    assert db.rolled_back


@pytest.mark.asyncio
async def test_invalid_arguments_rejected_with_reason():
    registry = make_registry()
    result = await registry.execute("read_chapter", {"chapter_index": "三"}, ToolContext(project_id=1))
    assert result.is_error
    assert "chapter_index" in result.error


@pytest.mark.asyncio
async def test_missing_required_argument_rejected():
    registry = make_registry()
    result = await registry.execute("read_chapter", {}, ToolContext(project_id=1))
    assert result.is_error
    assert "chapter_index" in result.error


@pytest.mark.asyncio
async def test_handler_exception_becomes_error_result():
    registry = ToolRegistry()

    @tool(registry=registry, name="boom", description="爆炸", permission="read",
          parameters={"type": "object", "properties": {}})
    async def boom(ctx: ToolContext) -> ToolResult:
        raise RuntimeError("数据库连接失败")

    result = await registry.execute("boom", {}, ToolContext(project_id=1))
    assert result.is_error
    assert "数据库连接失败" in result.error


@pytest.mark.asyncio
async def test_none_arguments_treated_as_unparseable():
    registry = make_registry()
    result = await registry.execute("read_chapter", None, ToolContext(project_id=1))
    assert result.is_error
    assert "JSON" in result.error or "参数" in result.error


def test_tool_definition_exposes_handler_metadata():
    registry = make_registry()
    definition = registry.get("read_chapter")
    assert isinstance(definition, ToolDefinition)
    assert definition.name == "read_chapter"
