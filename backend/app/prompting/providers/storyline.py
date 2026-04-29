import json

from app.core.model_call_trace import build_context_block
from app.models import Project, Setup
from app.prompting.providers.project import build_command_args_block


def build_setup_context_values(setup: Setup) -> dict[str, str]:
    return {
        "world_building": json.dumps(setup.world_building, ensure_ascii=False),
        "characters": json.dumps(setup.characters, ensure_ascii=False),
        "core_concept": json.dumps(setup.core_concept, ensure_ascii=False),
    }


def build_storyline_variables(project: Project, setup: Setup) -> dict:
    context = build_setup_context_values(setup)
    return {
        "name": project.name,
        "genre": project.genre,
        "world_building": context["world_building"],
        "characters": context["characters"],
        "core_concept": context["core_concept"],
    }


def build_storyline_context_blocks(
    setup: Setup,
    *,
    rendered_prompt: str,
    command_args: str | None = None,
) -> list[dict]:
    context = build_setup_context_values(setup)
    blocks = [
        build_context_block(key="setup_world_building", kind="setup", title="世界观", content=context["world_building"]),
        build_context_block(key="setup_characters", kind="setup", title="角色", content=context["characters"]),
        build_context_block(key="setup_core_concept", kind="setup", title="核心概念", content=context["core_concept"]),
        build_context_block(
            key="generate_storyline_template",
            kind="prompt_template",
            title="故事线生成提示词快照",
            content=rendered_prompt,
        ),
    ]
    if command_args and command_args.strip():
        blocks.append(build_command_args_block(command_args.strip()))
    return blocks
