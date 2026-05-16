import json
import re
from dataclasses import dataclass

from app.core.model_call_trace import build_context_block
from app.models import Project, Setup
from app.prompting.providers.project import build_command_args_block

SETUP_WORLD_CONTEXT_CHARS = 2000
SETUP_CHARACTERS_CONTEXT_CHARS = 2000
SETUP_CORE_CONCEPT_CONTEXT_CHARS = 1200
TRUNCATED_SETUP_CONTEXT_MARKER = "\n\n[已截断超长 Setup 内容，后续内容未进入本次生成上下文]"
UNICODE_ESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


@dataclass(frozen=True)
class SetupContextSnapshot:
    world_building: object
    characters: object
    core_concept: object


def build_setup_context_values(setup: Setup | SetupContextSnapshot) -> dict[str, str]:
    return {
        "world_building": _compact_json_context(setup.world_building, max_chars=SETUP_WORLD_CONTEXT_CHARS),
        "characters": _compact_json_context(setup.characters, max_chars=SETUP_CHARACTERS_CONTEXT_CHARS),
        "core_concept": _compact_json_context(setup.core_concept, max_chars=SETUP_CORE_CONCEPT_CONTEXT_CHARS),
    }


def build_storyline_variables(project: Project, setup: Setup | SetupContextSnapshot) -> dict:
    context = build_setup_context_values(setup)
    return {
        "name": project.name,
        "genre": project.genre,
        "world_building": context["world_building"],
        "characters": context["characters"],
        "core_concept": context["core_concept"],
    }


def build_storyline_context_blocks(
    setup: Setup | SetupContextSnapshot,
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


def _compact_json_context(value: object, *, max_chars: int) -> str:
    source_was_bounded = isinstance(value, str) and len(value) > max_chars
    content = _normalise_json_text(value) if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(content) <= max_chars:
        if source_was_bounded:
            return content.rstrip() + TRUNCATED_SETUP_CONTEXT_MARKER
        return content
    return content[:max_chars].rstrip() + TRUNCATED_SETUP_CONTEXT_MARKER


def _normalise_json_text(value: str) -> str:
    try:
        return json.dumps(json.loads(value), ensure_ascii=False)
    except ValueError:
        return UNICODE_ESCAPE_RE.sub(lambda match: chr(int(match.group(1), 16)), value)
