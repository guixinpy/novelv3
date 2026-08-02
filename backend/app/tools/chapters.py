"""章节读取与写入工具。"""
from __future__ import annotations

from app.agent.tooling import ToolContext, ToolResult, tool
from app.core.entity_miner import (
    mine_entities_from_text,
    promoted_entity_names,
    register_entity_candidates,
)
from domain.writing.format_checker import check_chapter_hook, check_text_format
from app.core.longform_memory import get_or_create_longform_memory
from domain.writing.structural_similarity import _CLUSTER_MIN, detect_structure_repeats
from app.models import ChapterContent, LongformMemory, Project, Setup, WorldCharacter, WorldLocation
from app.tools.registry import registry

_CLUSTER_MIN_CHAPTERS = _CLUSTER_MIN


def _register_mined_entities(ctx: ToolContext, content: str, chapter_index: int) -> None:
    """实体登记来源扩展：正文规则提取候选写入 entity_candidates（rule 通道）。"""
    names = mine_entities_from_text(content or "")
    if names:
        register_entity_candidates(ctx.db, ctx.project_id, chapter_index, names, source="rule")


def _chapter_summary(ch: ChapterContent) -> dict:
    return {
        "chapter_index": ch.chapter_index,
        "title": ch.title,
        "status": ch.status,
        "word_count": ch.word_count,
    }


@tool(
    registry=registry,
    name="list_chapters",
    description=(
        "列出项目的章节清单（序号、标题、状态、字数），按章节序号升序。"
        "想了解整体进度或定位某一章时先用本工具。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "start": {"type": "integer", "description": "起始章节序号（含），默认从第一章开始"},
            "limit": {"type": "integer", "description": "最多返回多少章，默认 50"},
        },
    },
)
async def list_chapters(ctx: ToolContext, start: int = 0, limit: int = 50) -> ToolResult:
    query = (
        ctx.db.query(ChapterContent)
        .filter(ChapterContent.project_id == ctx.project_id)
    )
    total = query.count()
    chapters = (
        query.filter(ChapterContent.chapter_index >= start)
        .order_by(ChapterContent.chapter_index.asc())
        .limit(limit)
        .all()
    )
    return ToolResult.ok({"total": total, "chapters": [_chapter_summary(c) for c in chapters]})


@tool(
    registry=registry,
    name="read_chapter",
    description="读取指定章节的完整正文与元数据。需要章节具体内容时使用。",
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "章节序号"},
        },
        "required": ["chapter_index"],
    },
)
async def read_chapter(ctx: ToolContext, chapter_index: int) -> ToolResult:
    chapter = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        existing = (
            ctx.db.query(ChapterContent.chapter_index)
            .filter(ChapterContent.project_id == ctx.project_id)
            .order_by(ChapterContent.chapter_index.asc())
            .all()
        )
        indexes = [row[0] for row in existing]
        hint = f"现有章节序号：{indexes[:50]}" if indexes else "项目还没有任何章节"
        return ToolResult.fail(
            f"第 {chapter_index} 章不存在。{hint}。可先用 list_chapters 查看章节清单。"
        )
    return ToolResult.ok(
        {
            **_chapter_summary(chapter),
            "content": chapter.content,
            "updated_at": chapter.updated_at.isoformat() if chapter.updated_at else None,
        }
    )


def _capture_entities(ctx: ToolContext, content: str, chapter_index: int) -> None:
    """从章节内容中提取已知实体名称并创建长期记忆记录。"""
    known_entities: dict[str, str] = {}
    for c in ctx.db.query(WorldCharacter).filter(WorldCharacter.project_id == ctx.project_id).all():
        known_entities[c.name] = "character"
    for l in ctx.db.query(WorldLocation).filter(WorldLocation.project_id == ctx.project_id).all():
        known_entities[l.name] = "location"
    # update_setup 写入的角色（Setups 表）也作为已知实体，否则 entity_state 记忆永远为空
    setup = ctx.db.query(Setup).filter(Setup.project_id == ctx.project_id).first()
    if setup is not None and setup.characters:
        for ch in setup.characters:
            if isinstance(ch, dict) and ch.get("name"):
                known_entities[str(ch["name"])] = "character"
    # 实体登记来源扩展：转正候选（rule 跨 ≥2 章 / l2 免转正）并入白名单
    for name in promoted_entity_names(ctx.db, ctx.project_id):
        known_entities.setdefault(name, "character")

    for name, etype in known_entities.items():
        if name in content:
            # T2 R2：统一 upsert（存在则更新出场章与状态，不存在则创建）
            get_or_create_longform_memory(
                ctx.db, ctx.project_id, "entity_state", name,
                defaults={
                    "title": name,
                    "summary": f"「{name}」出现在第 {chapter_index} 章",
                    "start_chapter_index": chapter_index,
                    "status": "active",
                },
                updates={"end_chapter_index": chapter_index, "status": "active"},
            )


def _update_project_word_count(ctx: ToolContext) -> None:
    """重算并更新项目总字数。"""
    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    if project is None:
        return
    total = (
        ctx.db.query(ChapterContent.word_count)
        .filter(ChapterContent.project_id == ctx.project_id)
        .all()
    )
    project.current_word_count = sum(wc for (wc,) in total)


@tool(
    registry=registry,
    name="write_chapter",
    description=(
        "创建或覆盖指定章节的正文。如果该章节已存在，会用新内容替换旧内容。"
        "写入完成后会自动更新项目的总字数。写入前建议先用 read_chapter 确认章节当前内容。"
    ),
    permission="write",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "章节序号，从 1 开始"},
            "content": {"type": "string", "description": "章节正文"},
            "title": {"type": "string", "description": "章节标题（可选，不传则保留旧标题或使用默认标题）"},
        },
        "required": ["chapter_index", "content"],
    },
)
async def write_chapter(ctx: ToolContext, chapter_index: int, content: str, title: str = "") -> ToolResult:
    if chapter_index < 1:
        return ToolResult.fail("章节序号必须 >= 1。")

    existing = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )

    word_count = len(content.replace(" ", "").replace("\n", ""))
    if existing:
        existing.content = content
        if title:
            existing.title = title
        existing.word_count = word_count
        existing.status = "generated"
    else:
        ch = ChapterContent(
            project_id=ctx.project_id,
            chapter_index=chapter_index,
            title=title or f"第{chapter_index}章",
            content=content,
            word_count=word_count,
            status="generated",
        )
        ctx.db.add(ch)

    ctx.db.flush()  # 确保新数据在查询前可见
    # 实体登记来源扩展：正文规则提取候选（rule 通道）
    _register_mined_entities(ctx, content, chapter_index)
    _capture_entities(ctx, content, chapter_index)
    _update_project_word_count(ctx)
    # 首章写入后项目进入写作阶段（否则状态停留在 draft/setup，模型会反复补设定）
    project = ctx.db.query(Project).filter(Project.id == ctx.project_id).first()
    if project is not None and project.status in ("draft", "setup"):
        project.status = "writing"
        project.current_phase = "content"
    ctx.db.commit()
    return ToolResult.ok({"chapter_index": chapter_index, "word_count": word_count, "status": "written"})


@tool(
    registry=registry,
    name="revise_chapter",
    description=(
        "对已存在的章节应用修订：替换完整正文为新内容。"
        "使用前需要先用 read_chapter 读取当前内容。"
    ),
    permission="write",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "要修订的章节序号"},
            "new_content": {"type": "string", "description": "修订后的完整正文"},
            "new_title": {"type": "string", "description": "可选的新标题"},
        },
        "required": ["chapter_index", "new_content"],
    },
)
async def revise_chapter(ctx: ToolContext, chapter_index: int, new_content: str, new_title: str = "") -> ToolResult:
    chapter = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        return ToolResult.fail(f"第 {chapter_index} 章不存在。请先用 write_chapter 创建或 list_chapters 确认。")

    chapter.content = new_content
    chapter.word_count = len(new_content.replace(" ", "").replace("\n", ""))
    if new_title:
        chapter.title = new_title
    ctx.db.flush()
    _register_mined_entities(ctx, new_content, chapter_index)
    _capture_entities(ctx, new_content, chapter_index)
    _update_project_word_count(ctx)
    ctx.db.commit()
    return ToolResult.ok({"chapter_index": chapter_index, "word_count": chapter.word_count, "status": "revised"})


@tool(
    registry=registry,
    name="check_chapter_quality",
    description=(
        "对指定章节做质量检查：字数范围、标题完整性、内容形式问题。"
        "如果返回的问题列表为空，说明章节质量基础过关。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "要检查的章节序号"},
        },
        "required": ["chapter_index"],
    },
)
async def check_chapter_quality(ctx: ToolContext, chapter_index: int) -> ToolResult:
    chapter = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        return ToolResult.fail(f"第 {chapter_index} 章不存在。")

    issues = []
    content = chapter.content or ""
    word_count = len(content.replace(" ", "").replace("\n", ""))

    # 字数检查
    if word_count < 50:
        issues.append({"severity": "warning", "type": "too_short", "detail": f"字数仅 {word_count}，建议至少 500 字"})
    elif word_count < 500:
        issues.append({"severity": "info", "type": "slightly_short", "detail": f"字数 {word_count}，偏短"})
    elif word_count > 50000:
        issues.append({"severity": "warning", "type": "too_long", "detail": f"字数 {word_count}，超过 50000 字建议拆分"})

    # 标题检查
    if not chapter.title or chapter.title.strip() == "":
        issues.append({"severity": "error", "type": "missing_title", "detail": "章节标题为空"})

    # 内容检查
    if not content.strip():
        issues.append({"severity": "error", "type": "empty_content", "detail": "章节正文为空"})
    elif len(content.strip()) < 10:
        issues.append({"severity": "error", "type": "placeholder_content", "detail": "章节正文过短，可能为占位内容"})

    return ToolResult.ok({
        "chapter_index": chapter_index,
        "title": chapter.title,
        "word_count": word_count,
        "status": chapter.status,
        "issues": issues,
        "quality": "pass" if not issues or all(i["severity"] == "info" for i in issues) else "needs_review",
    })


# ── T4: 输出格式守门员 ──


@tool(
    registry=registry,
    name="check_chapter_format",
    description=(
        "对指定章节做输出格式校验与章末卡点校验：markdown 加粗残留、备选词残留（X/Y）、"
        "正文自带章题行、全角引号成对、半角标点混用，以及章末是否缺乏悬念钩子。"
        "写完一章后建议立即调用；quality=fail 时请重写该章，needs_review 时请修正提示项。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "chapter_index": {"type": "integer", "description": "要检查的章节序号"},
        },
        "required": ["chapter_index"],
    },
)
async def check_chapter_format(ctx: ToolContext, chapter_index: int) -> ToolResult:
    chapter = (
        ctx.db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == ctx.project_id,
            ChapterContent.chapter_index == chapter_index,
        )
        .first()
    )
    if chapter is None:
        return ToolResult.fail(f"第 {chapter_index} 章不存在。")

    content = chapter.content or ""
    issues = check_text_format(content)
    issues.extend(check_chapter_hook(content))
    has_error = any(i["severity"] == "error" for i in issues)
    quality = "fail" if has_error else ("pass" if not issues else "needs_review")
    return ToolResult.ok({
        "chapter_index": chapter_index,
        "title": chapter.title,
        "quality": quality,
        "issues": issues,
    })


# ── T5: 结构级重复检测 ──


@tool(
    registry=registry,
    name="check_structure_repeat",
    description=(
        "检测最近 N 章是否存在标题重复（规范化后相同的标题出现 ≥2 次）。"
        "repeated=true 时请更换标题，避免同一主题循环。每写完一个副本/卷末建议调用。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "window": {
                "type": "integer",
                "description": "检查最近几章，默认 30，上限 60",
                "default": 30,
            },
        },
    },
)
async def check_structure_repeat(ctx: ToolContext, window: int = 30) -> ToolResult:
    window = max(1, min(window, 60))
    chapters = (
        ctx.db.query(ChapterContent)
        .filter(ChapterContent.project_id == ctx.project_id)
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    if len(chapters) < _CLUSTER_MIN_CHAPTERS:
        return ToolResult.ok({
            "repeated": False,
            "issues": [],
            "note": f"章节不足 {_CLUSTER_MIN_CHAPTERS} 章，无法做结构重复检测。",
        })

    recent = chapters[-window:]
    issues = detect_structure_repeats([
        {"index": c.chapter_index, "title": c.title or "", "content": c.content or ""}
        for c in recent
    ])
    return ToolResult.ok({
        "repeated": bool(issues),
        "issues": issues,
        "checked_window": len(recent),
        "tip": (
            "检测到模板循环时，请更换冲突类型、人物关系或解法；"
            "若接近卷尾，按 plan_arc 终局约束集中收束而非开新副本。"
        ) if issues else "未发现结构级重复。",
    })


# ── M5.2: Quality Trend Analysis ──


@tool(
    registry=registry,
    name="check_quality_trend",
    description=(
        "分析最近 N 章的质量趋势：查看章节长度变化曲线，检测是否有持续下滑。"
        "【跨弧线对比】写作跨越多个弧线时，务必用本工具检查全局趋势（window≥20），"
        "确保新弧线的章节质量不低于已完成弧线。如果发现跨弧线衰减，"
        "请检查是否对新弧线投入了足够的情节构思和场景细节。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "window": {
                "type": "integer",
                "description": "检查最近几章，默认 10",
                "default": 10,
            },
        },
    },
)
async def check_quality_trend(ctx: ToolContext, window: int = 10) -> ToolResult:
    chapters = (
        ctx.db.query(ChapterContent)
        .filter(ChapterContent.project_id == ctx.project_id)
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    if not chapters:
        return ToolResult.ok({"trend": "no_data", "tip": "还没有章节数据。"})

    # Take last N chapters
    recent = chapters[-window:]
    if len(recent) < 3:
        return ToolResult.ok({"trend": "insufficient_data", "tip": f"只有 {len(recent)} 章，至少需要 3 章才能分析趋势。"})

    word_counts = []
    titles = []
    for c in recent:
        content = c.content if c.content else ""
        wc = len(content) if content else 0
        word_counts.append(wc)
        titles.append(c.title or f"Ch{c.chapter_index}")

    # Compute trend
    first_half_avg = sum(word_counts[:len(word_counts)//2]) / max(1, len(word_counts)//2)
    second_half_avg = sum(word_counts[len(word_counts)//2:]) / max(1, len(word_counts) - len(word_counts)//2)
    ratio = second_half_avg / max(1, first_half_avg)
    min_wc = min(word_counts)
    max_wc = max(word_counts)

    if ratio < 0.5:
        trend = "severe_decline"
        advice = (
            f"严重下滑：近 {window} 章的字数从平均 {int(first_half_avg)} 字降至 {int(second_half_avg)} 字"
            f"（降幅 {int((1-ratio)*100)}%）。请立即检查："
            f"1) 主线是否已完结？如果是，用 plan_arc define 规划新弧线；"
            f"2) 是否在写填充内容（番外/后记）？应聚焦主线情节；"
            f"3) 是否需要补充更多场景、对话、描写来充实内容。"
        )
    elif ratio < 0.75:
        trend = "declining"
        advice = (
            f"轻度下滑：近 {window} 章字数从平均 {int(first_half_avg)} 降至 {int(second_half_avg)}"
            f"（降幅 {int((1-ratio)*100)}%）。注意质量控制，检查是否在接近弧线尾声。"
        )
    elif ratio > 1.3:
        trend = "growing"
        advice = f"字数增长中：从 {int(first_half_avg)} → {int(second_half_avg)}（+{int((ratio-1)*100)}%），保持势头。"
    else:
        trend = "stable"
        advice = f"字数稳定：{int(first_half_avg)} → {int(second_half_avg)}，质量趋势正常。"

    result: dict = {
        "trend": trend,
        "window": len(recent),
        "word_counts": [
            {"chapter_index": recent[i].chapter_index, "title": titles[i], "word_count": word_counts[i]}
            for i in range(len(recent))
        ],
        "first_half_avg": int(first_half_avg),
        "second_half_avg": int(second_half_avg),
        "min": min_wc,
        "max": max_wc,
        "ratio": round(ratio, 2),
        "advice": advice,
    }

    # T3 R3：终局核对——活跃弧线接近收束章（≤5 章）且仍有未回收伏笔 → 强制回收模式
    active_arc = (
        ctx.db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == ctx.project_id,
            LongformMemory.memory_type == "story_arc",
            LongformMemory.status == "active",
        )
        .first()
    )
    endgame = (active_arc.memory_metadata or {}).get("endgame") if active_arc is not None else None
    if endgame:
        latest_index = chapters[-1].chapter_index
        resolve_before = int(endgame.get("resolve_before") or 0)
        remaining = max(0, resolve_before - latest_index)
        must_resolve = endgame.get("must_resolve") or []
        must_open = []
        for item in must_resolve:
            hit = (
                ctx.db.query(LongformMemory)
                .filter(
                    LongformMemory.project_id == ctx.project_id,
                    LongformMemory.memory_type == "plotline",
                    LongformMemory.scope_key.like(f"%{item}%"),
                    LongformMemory.status == "open",
                )
                .first()
            )
            if hit is not None:
                must_open.append(item)
        if remaining <= 5:
            result["endgame_mode"] = True
            result["endgame_remaining"] = remaining
            result["must_resolve_open"] = must_open
            result["endgame_advice"] = (
                f"本卷剩余 {remaining} 章。未回收伏笔："
                f"{'、'.join(must_open) if must_open else '(无)'}。"
                f"请进入回收模式：优先收束开放伏笔，暂缓开新线。"
            )
        else:
            result["endgame_mode"] = False
    else:
        result["endgame_mode"] = False

    return ToolResult.ok(result)
