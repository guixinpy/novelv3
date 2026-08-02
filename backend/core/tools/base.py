"""工具框架：注册 / 权限 / pydantic schema 校验 / 失败分类 / 结果归一化。

吸收点：
- pydantic model 生成 JSON-schema（消除手写 schema 漂移，修旧缺陷 #4）
- 失败分类学 ClassifiedFailure（openhuman）：guard 按 error_code 判断，不再字符串耦合（修旧缺陷 #3）
- 结果归一化契约（hermes）：handler 返回值收敛为 str / ToolResult，违规转结构化错误
- 工具异常回填给模型而非炸循环（保留旧验证过的行为）
"""
from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ValidationError

from core.providers.base import ToolSpec


class PermissionLevel(StrEnum):
    READ = "read"          # 直接执行
    PROPOSE = "propose"    # 产生提案，待审批后生效
    WRITE = "write"        # 经审批门执行


class FailureCategory(StrEnum):
    VALIDATION = "validation"      # 参数/格式错误——模型可自行修正
    UNKNOWN_TOOL = "unknown_tool"  # 幻觉工具名
    TRANSIENT = "transient"        # 可重试（网络/限流）
    PERMANENT = "permanent"        # 不可恢复
    PERMISSION = "permission"      # 权限/审批拒绝
    INTERNAL = "internal"          # 实现内部错误


@dataclass
class ToolContext:
    """工具执行上下文。session 级资源（db、project）由 harness 填充。

    db 为 Any：内核不依赖具体持久化技术。
    """

    project_id: str | None = None
    session_id: str | None = None
    db: Any = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArtifactRef:
    """工具结果三级治理的第三级：大产出落盘，回传路径指针。

    path 必须经过 validate_artifact_path 校验（拒绝绝对路径/..）。
    """

    path: str
    bytes: int = 0
    summary: str = ""


@dataclass(frozen=True)
class ToolResult:
    data: Any = None
    error: str | None = None
    error_code: str = ""                      # 机器可读错误码（护栏判断依据）
    category: FailureCategory | None = None   # 失败分类（可恢复性）
    artifact: ArtifactRef | None = None       # 落盘产物指针

    @property
    def is_error(self) -> bool:
        return self.error is not None

    @staticmethod
    def ok(data: Any, artifact: ArtifactRef | None = None) -> ToolResult:
        return ToolResult(data=data, artifact=artifact)

    @staticmethod
    def fail(
        error: str,
        error_code: str = "tool_failed",
        category: FailureCategory = FailureCategory.INTERNAL,
    ) -> ToolResult:
        return ToolResult(error=error, error_code=error_code, category=category)

    def to_model_text(self) -> str:
        if self.is_error:
            return json.dumps({"error": self.error}, ensure_ascii=False)
        return json.dumps(self.data, ensure_ascii=False, default=str)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    args_model: type[BaseModel] | None
    permission: PermissionLevel
    handler: Callable

    def to_spec(self) -> ToolSpec:
        # pydantic v2 的 json schema 含 "$defs"，多数 provider 接受；description 已在模型 docstring
        parameters = self.args_model.model_json_schema() if self.args_model is not None else {}
        return ToolSpec(name=self.name, description=self.description, parameters=parameters)


def _normalize_handler_result(name: str, raw: Any) -> ToolResult:
    """结果归一化契约（hermes #6）：handler 只允许返回 str / ToolResult，违规转结构化错误。"""
    if isinstance(raw, ToolResult):
        return raw
    if isinstance(raw, str):
        return ToolResult.ok(raw)
    if raw is None:
        return ToolResult.ok(None)
    return ToolResult.fail(
        f"工具「{name}」返回了不支持的类型 {type(raw).__name__}（应返回 str 或 ToolResult）。",
        error_code="tool_result_contract",
        category=FailureCategory.INTERNAL,
    )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"tool {definition.name} already registered")
        self._tools[definition.name] = definition

    def get(self, name: str) -> ToolDefinition:
        return self._tools[name]

    def names(self) -> list[str]:
        return list(self._tools)

    def to_specs(self) -> list[ToolSpec]:
        return [d.to_spec() for d in self._tools.values()]

    async def execute(self, name: str, arguments: dict | None, ctx: ToolContext) -> ToolResult:
        definition = self._tools.get(name)
        if definition is None:
            return ToolResult.fail(
                f"工具 {name} 不存在。可用工具：{sorted(self._tools)}。请改用其中之一。",
                error_code="unknown_tool",
                category=FailureCategory.UNKNOWN_TOOL,
            )
        if arguments is None:
            return ToolResult.fail(
                "参数不是合法 JSON 对象。请以 JSON object 形式重新提供参数。",
                error_code="validation",
                category=FailureCategory.VALIDATION,
            )
        # pydantic 校验（含必填/类型/约束）。未知参数显式报错而非静默丢弃
        # （旧 pydantic 默认 extra=ignore 吞掉模型猜测参数，模型学不到正确 schema——
        # code-review #12）
        if definition.args_model is not None:
            unknown = sorted(set(arguments) - set(definition.args_model.model_fields))
            if unknown:
                known = sorted(definition.args_model.model_fields)
                example = _example_arguments(definition.args_model)
                return ToolResult.fail(
                    f"未知参数 {unknown}。本工具可用参数：{known}。"
                    f"参数示例：{json.dumps(example, ensure_ascii=False)}。",
                    error_code="validation",
                    category=FailureCategory.VALIDATION,
                )
            try:
                validated = definition.args_model.model_validate(arguments)
                resolved: dict[str, Any] = validated.model_dump()
            except ValidationError as exc:
                errors = "; ".join(f"{e['loc']}: {e['msg']}" for e in exc.errors()[:5])
                example = _example_arguments(definition.args_model)
                return ToolResult.fail(
                    f"参数校验失败：{errors}。参数示例：{json.dumps(example, ensure_ascii=False)}。",
                    error_code="validation",
                    category=FailureCategory.VALIDATION,
                )
        else:
            resolved = arguments
        try:
            result = definition.handler(ctx, **resolved)
            if inspect.isawaitable(result):
                result = await result
            return _normalize_handler_result(name, result)
        except Exception as exc:  # noqa: BLE001 - 工具异常必须回填给模型而非炸毁循环
            _rollback(ctx)
            return ToolResult.fail(
                f"工具 {name} 执行失败：{exc}。可调整参数重试或改用其他工具。",
                error_code="tool_execution_error",
                category=FailureCategory.INTERNAL,
            )


def _rollback(ctx: ToolContext) -> None:
    """数据库事务失败后必须 rollback，否则同请求内后续工具全部报
    "transaction has been rolled back"（M4 dogfood 实测暴露）。"""
    db = getattr(ctx, "db", None)
    rollback = getattr(db, "rollback", None)
    if callable(rollback):
        with suppress(Exception):
            rollback()


def _example_arguments(args_model: type[BaseModel]) -> dict:
    """从 pydantic model 生成参数示例 JSON（只含 required），供错误信息展示。"""
    schema = args_model.model_json_schema()
    properties: dict = schema.get("properties", {})
    example: dict = {}
    for name in schema.get("required", []):
        type_name = properties.get(name, {}).get("type", "string")
        if type_name == "integer":
            example[name] = 1
        elif type_name == "number":
            example[name] = 1.0
        elif type_name == "boolean":
            example[name] = True
        elif type_name == "array":
            example[name] = []
        elif type_name == "object":
            example[name] = {}
        else:
            example[name] = name  # string 用参数名做示例文本
    return example


def tool(
    *,
    registry: ToolRegistry,
    name: str,
    description: str,
    args_model: type[BaseModel] | None = None,
    permission: str = "read",
) -> Callable:
    def decorator(fn: Callable) -> Callable:
        registry.register(
            ToolDefinition(
                name=name,
                description=description,
                args_model=args_model,
                permission=PermissionLevel(permission),
                handler=fn,
            )
        )
        return fn

    return decorator
