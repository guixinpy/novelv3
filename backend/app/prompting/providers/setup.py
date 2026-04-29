from app.core.model_call_trace import build_context_block
from app.models import Project
from app.prompting.providers.project import build_command_args_block, build_project_profile_block


def build_setup_variables(project: Project) -> dict:
    return {
        "name": project.name,
        "genre": project.genre,
        "description": project.description,
        "style": project.style,
        "complexity": project.complexity,
    }


def build_setup_context_blocks(
    project: Project,
    *,
    rendered_prompt: str,
    command_args: str | None = None,
) -> list[dict]:
    blocks = [
        build_project_profile_block(project),
        build_context_block(
            key="generate_setup_template",
            kind="prompt_template",
            title="设定生成提示词快照",
            content=rendered_prompt,
        ),
    ]
    if command_args and command_args.strip():
        blocks.append(build_command_args_block(command_args.strip()))
    return blocks
