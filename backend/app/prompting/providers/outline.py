import json

from app.core.model_call_trace import build_context_block
from app.models import Project, Setup, Storyline
from app.prompting.providers.project import build_command_args_block
from app.prompting.providers.storyline import SetupContextSnapshot, build_setup_context_values


def target_total_chapters(project: Project) -> int:
    if project.target_chapter_count and project.target_chapter_count > 0:
        return project.target_chapter_count
    if project.target_word_count and project.target_word_count > 0:
        return project.target_word_count // 3000 or 10
    return 10


def outline_max_tokens(project: Project) -> int:
    return min(max(4000, target_total_chapters(project) * 400), 12000)


def build_storyline_context_value(storyline: Storyline | str) -> str:
    if isinstance(storyline, str):
        return storyline
    return json.dumps(
        {"plotlines": storyline.plotlines, "foreshadowing": storyline.foreshadowing},
        ensure_ascii=False,
    )


def build_outline_variables(project: Project, setup: Setup | SetupContextSnapshot, storyline: Storyline | str) -> dict:
    setup_context = build_setup_context_values(setup)
    return {
        "name": project.name,
        "world_building": setup_context["world_building"],
        "characters": setup_context["characters"],
        "core_concept": setup_context["core_concept"],
        "storyline": build_storyline_context_value(storyline),
        "total_chapters": target_total_chapters(project),
    }


def build_outline_context_blocks(
    project: Project,
    setup: Setup | SetupContextSnapshot,
    storyline: Storyline | str,
    *,
    rendered_prompt: str,
    command_args: str | None = None,
) -> list[dict]:
    setup_context = build_setup_context_values(setup)
    storyline_context = build_storyline_context_value(storyline)
    total_chapters = target_total_chapters(project)
    blocks = [
        build_context_block(key="setup_world_building", kind="setup", title="世界观", content=setup_context["world_building"]),
        build_context_block(key="setup_characters", kind="setup", title="角色", content=setup_context["characters"]),
        build_context_block(key="setup_core_concept", kind="setup", title="核心概念", content=setup_context["core_concept"]),
        build_context_block(key="storyline_context", kind="storyline", title="故事线", content=storyline_context),
        build_context_block(
            key="outline_target",
            kind="generation_constraint",
            title="大纲目标",
            content=json.dumps({"total_chapters": total_chapters}, ensure_ascii=False),
        ),
        build_context_block(
            key="generate_outline_template",
            kind="prompt_template",
            title="大纲生成提示词快照",
            content=rendered_prompt,
        ),
    ]
    if command_args and command_args.strip():
        blocks.append(build_command_args_block(command_args.strip()))
    return blocks
