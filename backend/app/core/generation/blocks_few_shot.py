from app.core.few_shot_library import FewShotExampleLibrary
from app.core.model_call_trace import build_context_block
from app.models import Project


def build_few_shot_examples_block(project: Project, *, task_type: str = "chapter") -> dict | None:
    library = FewShotExampleLibrary()
    examples = library.select_examples(task_type, project.genre)
    if not examples:
        return None

    return build_context_block(
        key="few_shot_examples",
        kind="few_shot",
        title="章节示例",
        content=library.format_for_prompt(examples),
        sources=[
            {
                "source_type": "FewShotExampleLibrary",
                "source_id": project.genre,
                "label": f"Few-shot examples for {project.genre}",
                "source_ref": f"few_shot:{task_type}:{project.genre}",
                "metadata": {"task_type": task_type, "example_count": len(examples)},
            }
        ],
    )
