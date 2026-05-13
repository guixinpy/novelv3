import json
import re

from sqlalchemy.orm import Session

from app.core.model_call_trace import build_context_block
from app.models import ChapterContent, Outline, Project, Setup
from app.prompting.providers.athena import athena_context_has_retrieval, build_athena_chapter_context_block
from app.prompting.providers.few_shot import build_few_shot_examples_block
from app.prompting.providers.longform import build_longform_context_block
from app.prompting.providers.retrieval import build_chapter_retrieval_block
from app.prompting.providers.style import build_style_rule_block

CHAPTER_CONTEXT_CHAR_BUDGET = 24000
PRIORITY_USER_FEEDBACK = 0
PRIORITY_LENGTH_CONSTRAINT = 1
PRIORITY_CHAPTER_TARGET = 10
PRIORITY_LONGFORM_CONTEXT = 18
PRIORITY_ATHENA_CONTEXT = 20
PRIORITY_RETRIEVAL_EVIDENCE = 30
PRIORITY_PREVIOUS_CHAPTER = 40
PRIORITY_STYLE_RULE = 50
PRIORITY_FEW_SHOT = 60
PRIORITY_SETUP_WORLD = 80
PRIORITY_SETUP_CORE_CONCEPT = 82
PRIORITY_SETUP_CHARACTERS = 85


def build_chapter_prompt_variables(project: Project, setup: Setup, chapter_index: int) -> dict:
    return {
        "chapter_index": chapter_index,
        "language": project.language,
    }


def build_chapter_prompt_context_blocks(
    db: Session,
    project: Project,
    setup: Setup,
    chapter_index: int,
    extra_feedback: str,
) -> tuple[list[dict], list[dict]]:
    model_blocks: list[dict] = [
        _prioritized(
            build_context_block(
                key="setup_world_building",
                kind="setup",
                title="世界观",
                content=json.dumps(setup.world_building, ensure_ascii=False),
            ),
            PRIORITY_SETUP_WORLD,
        ),
        _prioritized(
            build_context_block(
                key="setup_characters",
                kind="setup",
                title="角色",
                content=json.dumps(setup.characters, ensure_ascii=False),
            ),
            PRIORITY_SETUP_CHARACTERS,
        ),
        _prioritized(
            build_context_block(
                key="setup_core_concept",
                kind="setup",
                title="核心概念",
                content=json.dumps(setup.core_concept, ensure_ascii=False),
            ),
            PRIORITY_SETUP_CORE_CONCEPT,
        ),
    ]
    trace_only_blocks: list[dict] = []

    outline_block = _build_outline_chapter_target_block(db, project.id, chapter_index)
    if outline_block:
        model_blocks.append(_prioritized(outline_block, PRIORITY_CHAPTER_TARGET))

    previous_block = _build_previous_chapter_summary_block(db, project.id, chapter_index)
    if previous_block:
        model_blocks.append(_prioritized(previous_block, PRIORITY_PREVIOUS_CHAPTER))

    longform_block, _longform_package, longform_error_block = build_longform_context_block(
        db,
        project_id=project.id,
        chapter_index=chapter_index,
        user_query=extra_feedback,
    )
    if longform_block:
        model_blocks.append(_prioritized(longform_block, PRIORITY_LONGFORM_CONTEXT))
    if longform_error_block:
        trace_only_blocks.append(longform_error_block)

    athena_block, athena_package, athena_error_block = build_athena_chapter_context_block(
        db,
        project_id=project.id,
        chapter_index=chapter_index,
    )
    if athena_block:
        model_blocks.append(_prioritized(athena_block, PRIORITY_ATHENA_CONTEXT))
    if athena_error_block:
        trace_only_blocks.append(athena_error_block)

    retrieval_block, _retrieval_context, retrieval_error_block = build_chapter_retrieval_block(
        db,
        project_id=project.id,
        chapter_index=chapter_index,
    )
    if retrieval_error_block:
        trace_only_blocks.append(retrieval_error_block)
    if retrieval_block:
        if athena_context_has_retrieval(athena_package):
            retrieval_block = _prioritized(retrieval_block, PRIORITY_RETRIEVAL_EVIDENCE)
            retrieval_block["metadata"] = {
                **retrieval_block.get("metadata", {}),
                "trace_only": True,
                "model_injection": "skipped_existing_in_athena_context",
            }
            trace_only_blocks.append(retrieval_block)
        else:
            model_blocks.append(_prioritized(retrieval_block, PRIORITY_RETRIEVAL_EVIDENCE))

    style_block = build_style_rule_block(project)
    if style_block:
        model_blocks.append(_prioritized(style_block, PRIORITY_STYLE_RULE))

    few_shot_block = build_few_shot_examples_block(project)
    if few_shot_block:
        model_blocks.append(_prioritized(few_shot_block, PRIORITY_FEW_SHOT))

    if extra_feedback:
        model_blocks.append(
            _prioritized(
                build_context_block(
                    key="extra_feedback",
                    kind="user_feedback",
                    title="用户修订反馈",
                    content=extra_feedback,
                ),
                PRIORITY_USER_FEEDBACK,
            )
        )
        length_constraint = build_length_constraint(extra_feedback)
        if length_constraint:
            model_blocks.append(
                _prioritized(
                    build_context_block(
                        key="length_constraint",
                        kind="generation_constraint",
                        title="长度约束",
                        content=length_constraint,
                    ),
                    PRIORITY_LENGTH_CONSTRAINT,
                )
            )

    return model_blocks, trace_only_blocks


def build_chapter_trace_context_blocks(
    rendered_prompt: str,
    prompt_context_blocks: list[dict],
    trace_only_context_blocks: list[dict] | None = None,
) -> list[dict]:
    return [
        *prompt_context_blocks,
        *(trace_only_context_blocks or []),
        build_context_block(
            key="generate_chapter_template",
            kind="prompt_template",
            title="章节生成提示词快照",
            content=rendered_prompt,
        ),
    ]


def chapter_max_tokens(extra_feedback: str) -> int:
    word_range = extract_word_range(extra_feedback)
    if not word_range:
        return 4000
    return min(4000, max(word_range[1] + 800, 1200))


def build_length_constraint(extra_feedback: str) -> str | None:
    word_range = extract_word_range(extra_feedback)
    if not word_range:
        return None
    return (
        f"正文长度控制在{word_range[0]}-{word_range[1]}字，"
        "不要为了解释设定而扩写，优先保证剧情推进和章节钩子。"
    )


def extract_word_range(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d{3,5})\s*(?:-|~|至|到|—|－)\s*(\d{3,5})\s*字", text or "")
    if not match:
        return None
    low, high = int(match.group(1)), int(match.group(2))
    if low <= 0 or high < low:
        return None
    return low, high


def _build_outline_chapter_target_block(db: Session, project_id: str, chapter_index: int) -> dict | None:
    outline = db.query(Outline).filter(Outline.project_id == project_id).first()
    if not outline or not outline.chapters:
        return None
    for chapter_outline in outline.chapters:
        if not isinstance(chapter_outline, dict):
            continue
        if chapter_outline.get("chapter_index") != chapter_index:
            continue
        title = chapter_outline.get("title", "")
        summary = chapter_outline.get("summary", "")
        lines = [f"{title}：{summary}".strip("：")]
        if chapter_outline.get("scenes"):
            lines.append(f"场景：{'、'.join(chapter_outline['scenes'])}")
        if chapter_outline.get("characters"):
            lines.append(f"出场角色：{'、'.join(chapter_outline['characters'])}")
        return build_context_block(
            key="outline_chapter_target",
            kind="outline",
            title="本章大纲",
            content="\n".join(line for line in lines if line),
            sources=[
                {
                    "source_type": "Outline",
                    "source_id": project_id,
                    "label": f"第{chapter_index}章大纲",
                    "source_ref": f"Outline.chapters[{chapter_index}]",
                    "metadata": {"chapter_index": chapter_index},
                }
            ],
        )
    return None


def _build_previous_chapter_summary_block(db: Session, project_id: str, chapter_index: int) -> dict | None:
    if chapter_index <= 1:
        return None
    previous = (
        db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index == chapter_index - 1,
        )
        .first()
    )
    if not previous or not previous.content:
        return None
    summary = previous.content[:300] + "..." if len(previous.content) > 300 else previous.content
    return build_context_block(
        key="previous_chapter_summary",
        kind="chapter_summary",
        title="上一章摘要",
        content=summary,
        sources=[
            {
                "source_type": "ChapterContent",
                "source_id": previous.id,
                "label": previous.title or f"第{chapter_index - 1}章",
                "source_ref": f"chapter:{chapter_index - 1}",
                "metadata": {"chapter_index": chapter_index - 1},
            }
        ],
    )


def _prioritized(block: dict, priority: int) -> dict:
    block["priority"] = priority
    return block
