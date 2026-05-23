from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_STATUS_OUTPUT = object_schema({"status": {"type": "string"}})
_COMMAND_ARGS_INPUT = object_schema({"command_args": {"type": "string"}})


HERMES_ACTION_AGENT_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="generate_setup",
        module="hermes",
        category="generation",
        description="根据项目意图生成小说基础设定。",
        input_schema=_COMMAND_ARGS_INPUT,
        output_schema=_STATUS_OUTPUT,
        target_type="setup",
        sort_key=20,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="generate_storyline",
        module="hermes",
        category="generation",
        description="基于设定生成叙事主线、支线和伏笔结构。",
        input_schema=_COMMAND_ARGS_INPUT,
        output_schema=_STATUS_OUTPUT,
        target_type="storyline",
        sort_key=30,
        availability_checks=("setup_exists",),
    ),
    AgentToolDescriptor(
        name="generate_outline",
        module="hermes",
        category="generation",
        description="基于设定和故事线生成章节大纲。",
        input_schema=_COMMAND_ARGS_INPUT,
        output_schema=_STATUS_OUTPUT,
        target_type="outline",
        sort_key=40,
        availability_checks=("setup_exists", "storyline_exists"),
    ),
)
