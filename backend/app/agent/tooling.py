"""工具注册与执行框架（CADR-003）：@tool 装饰器自注册 + 三级权限。

错误信息写给模型看：说明错在哪、下一步可以怎么做。
"""
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

from app.agent.providers.base import ToolSpec


class PermissionLevel(str, Enum):
    READ = "read"          # 直接执行
    PROPOSE = "propose"    # 产生提案，待审批后生效
    WRITE = "write"        # 经审批门执行


@dataclass
class ToolContext:
    """工具执行上下文。session 级资源（db、project）由 harness 填充。

    db 为 Any：内核不依赖具体持久化技术（CADR-005）。
    """

    project_id: str | None = None
    session_id: str | None = None
    db: Any = None
    extras: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    data: Any = None
    error: str | None = None

    @property
    def is_error(self) -> bool:
        return self.error is not None

    @staticmethod
    def ok(data: Any) -> "ToolResult":
        return ToolResult(data=data)

    @staticmethod
    def fail(error: str) -> "ToolResult":
        return ToolResult(error=error)

    def to_model_text(self) -> str:
        if self.is_error:
            return json.dumps({"error": self.error}, ensure_ascii=False)
        return json.dumps(self.data, ensure_ascii=False, default=str)


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    permission: PermissionLevel
    handler: Callable

    def to_spec(self) -> ToolSpec:
        return ToolSpec(name=self.name, description=self.description, parameters=self.parameters)


_JSON_TYPES: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _example_arguments(parameters: dict) -> dict:
    """从 schema 生成参数示例 JSON（只含 required 参数），供错误信息展示（T2 R1）。"""
    properties: dict = parameters.get("properties", {})
    example: dict = {}
    for name in parameters.get("required", []):
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


def _validate_arguments(parameters: dict, arguments: dict) -> str | None:
    """轻量 schema 校验：required + 顶层类型。返回 None 表示通过。

    错误信息附加参数示例（T2 R1：few-shot），让模型不用猜参数写法。
    """
    properties: dict = parameters.get("properties", {})
    example_suffix = f"参数示例：{json.dumps(_example_arguments(parameters), ensure_ascii=False)}"
    for name in parameters.get("required", []):
        if name not in arguments:
            return f"缺少必填参数 {name}。请补全后重试。{example_suffix}"
    for name, value in arguments.items():
        if name not in properties:
            return (
                f"未知参数 {name}。本工具可用参数：{sorted(properties)}。"
                f"{example_suffix}"
            )
        type_name = properties[name].get("type", "")
        expected = _JSON_TYPES.get(type_name)
        if expected is None:
            continue
        # bool 是 int 的子类，单独排除
        wrong_bool = isinstance(value, bool) and type_name in ("integer", "number")
        if wrong_bool or not isinstance(value, expected):
            return (
                f"参数 {name} 类型错误：期望 {type_name}，"
                f"收到 {type(value).__name__}。请改用正确类型重试。{example_suffix}"
            )
    return None


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
                f"工具 {name} 不存在。可用工具：{sorted(self._tools)}。请改用其中之一。"
            )
        if arguments is None:
            return ToolResult.fail("参数不是合法 JSON 对象。请以 JSON object 形式重新提供参数。")
        error = _validate_arguments(definition.parameters, arguments)
        if error:
            return ToolResult.fail(error)
        try:
            result = definition.handler(ctx, **arguments)
            if inspect.isawaitable(result):
                result = await result
            return result
        except Exception as exc:  # noqa: BLE001 - 工具异常必须回填给模型而非炸毁循环
            # 数据库事务失败后必须 rollback，否则同请求内后续工具全部报
            # "transaction has been rolled back"（M4 dogfood 实测暴露）
            db = getattr(ctx, "db", None)
            rollback = getattr(db, "rollback", None)
            if callable(rollback):
                try:
                    rollback()
                except Exception:
                    pass
            return ToolResult.fail(f"工具 {name} 执行失败：{exc}。可调整参数重试或改用其他工具。")


def tool(
    *,
    registry: ToolRegistry,
    name: str,
    description: str,
    parameters: dict,
    permission: str = "read",
) -> Callable:
    def decorator(fn: Callable) -> Callable:
        registry.register(
            ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                permission=PermissionLevel(permission),
                handler=fn,
            )
        )
        return fn

    return decorator
