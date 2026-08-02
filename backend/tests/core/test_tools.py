"""工具框架测试：pydantic schema 校验 / 失败分类 / 结果归一化 / artifact 路径。"""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.artifact import validate_artifact_path
from core.tools.base import (
    FailureCategory,
    ToolContext,
    ToolRegistry,
    ToolResult,
    tool,
)


class WriteArgs(BaseModel):
    chapter_index: int = Field(..., ge=1)
    content: str = Field(..., min_length=1)


def make_registry() -> ToolRegistry:
    registry = ToolRegistry()

    @tool(registry=registry, name="write_chapter", description="写章节", args_model=WriteArgs, permission="write")
    def write_chapter(ctx: ToolContext, chapter_index: int, content: str) -> ToolResult:
        return ToolResult.ok({"status": "written", "chapter_index": chapter_index})

    @tool(registry=registry, name="returns_str", description="返回字符串", args_model=None)
    def returns_str(ctx: ToolContext) -> str:
        return "plain text"

    @tool(registry=registry, name="returns_bad", description="返回非法类型", args_model=None)
    def returns_bad(ctx: ToolContext) -> int:
        return 42

    @tool(registry=registry, name="raises", description="抛异常", args_model=None)
    def raises(ctx: ToolContext) -> None:
        raise RuntimeError("内部炸了")

    return registry


async def test_pydantic_schema_generated():
    """修旧缺陷 #4：schema 由 pydantic 生成，不手写。"""
    registry = make_registry()
    specs = registry.to_specs()
    write_spec = next(s for s in specs if s.name == "write_chapter")
    assert write_spec.parameters["required"] == ["chapter_index", "content"]
    assert write_spec.parameters["properties"]["chapter_index"]["minimum"] == 1


async def test_validation_failure_category():
    registry = make_registry()
    result = await registry.execute("write_chapter", {"chapter_index": 0}, ToolContext())
    assert result.is_error
    assert result.error_code == "validation"
    assert result.category == FailureCategory.VALIDATION


async def test_unknown_tool_category():
    registry = make_registry()
    result = await registry.execute("ghost", {}, ToolContext())
    assert result.is_error
    assert result.error_code == "unknown_tool"
    assert result.category == FailureCategory.UNKNOWN_TOOL


async def test_result_normalization_contract():
    """结果归一化（hermes #6）：str 通过；非法类型转结构化错误。"""
    registry = make_registry()
    ok = await registry.execute("returns_str", {}, ToolContext())
    assert not ok.is_error and ok.data == "plain text"
    bad = await registry.execute("returns_bad", {}, ToolContext())
    assert bad.is_error
    assert bad.error_code == "tool_result_contract"


async def test_tool_exception_becomes_failure():
    registry = make_registry()
    result = await registry.execute("raises", {}, ToolContext())
    assert result.is_error
    assert result.error_code == "tool_execution_error"
    assert "内部炸了" in result.error


def test_artifact_path_fail_closed():
    """artifact 路径校验：拒绝绝对路径/..（openhuman fail-closed）。"""
    root = Path("/work")
    assert validate_artifact_path("chapters/ch1.md", root) is not None
    assert validate_artifact_path("ch1.md", root) is not None
    assert validate_artifact_path("/etc/passwd", root) is None
    assert validate_artifact_path("../escape.md", root) is None
    assert validate_artifact_path("a/../../escape.md", root) is None
    assert validate_artifact_path("", root) is None
    assert validate_artifact_path("..", root) is None


async def test_unknown_parameter_reports_error():
    """#12：未知参数显式报错回传模型（旧 extra=ignore 静默丢弃）。"""
    registry = make_registry()
    result = await registry.execute(
        "write_chapter", {"chapter_index": 1, "content": "正文", "tone": "悬疑"},
        ToolContext(),
    )
    assert result.is_error
    assert result.error_code == "validation"
    assert "tone" in result.error
    assert "chapter_index" in result.error  # 可用参数列表
