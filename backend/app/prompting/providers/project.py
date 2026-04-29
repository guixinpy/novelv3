import json

from app.core.model_call_trace import build_context_block
from app.models import Project


def build_project_profile(project: Project) -> dict:
    return {
        "name": project.name,
        "genre": project.genre,
        "description": project.description,
        "style": project.style,
        "complexity": project.complexity,
        "target_chapter_count": project.target_chapter_count,
        "target_word_count": project.target_word_count,
        "language": project.language,
    }


def build_project_profile_block(project: Project) -> dict:
    return build_context_block(
        key="project_profile",
        kind="project",
        title="项目基础信息",
        content=json.dumps(build_project_profile(project), ensure_ascii=False),
    )


def build_command_args_block(command_args: str) -> dict:
    return build_context_block(
        key="command_args",
        kind="user_feedback",
        title="用户附加要求",
        content=command_args,
    )
