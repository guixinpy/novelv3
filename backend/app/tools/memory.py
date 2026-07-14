"""长期记忆工具：情节线追踪和实体状态查询（M4）。"""
from __future__ import annotations

from datetime import UTC, datetime

from app.agent.tooling import ToolContext, ToolResult, tool
from app.core.athena_retrieval import search_retrieval
from app.models import LongformMemory
from app.tools.registry import registry


@tool(
    registry=registry,
    name="track_plotline",
    description=(
        "登记、查询或闭环一条情节线/伏笔。操作类型决定行为："
        "open=创建新情节线，close=闭环，query=查询。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["open", "close", "query"],
                "description": "操作类型",
            },
            "title": {"type": "string", "description": "情节线标题，如「林舟父亲失踪之谜」"},
            "summary": {"type": "string", "description": "情节线描述"},
            "chapter_index": {"type": "integer", "description": "当前章节序号"},
        },
        "required": ["action"],
    },
)
async def track_plotline(
    ctx: ToolContext,
    action: str,
    title: str = "",
    summary: str = "",
    chapter_index: int = 0,
) -> ToolResult:
    if action == "open":
        if not title:
            return ToolResult.fail("open 操作需要 title 参数。")
        existing = (
            ctx.db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == ctx.project_id,
                LongformMemory.memory_type == "plotline",
                LongformMemory.scope_key == title,
                LongformMemory.status == "open",
            )
            .first()
        )
        if existing:
            return ToolResult.ok({
                "action": "already_exists",
                "id": existing.id,
                "title": title,
                "status": "open",
            })
        mem = LongformMemory(
            project_id=ctx.project_id,
            memory_type="plotline",
            scope_key=title,
            title=title,
            summary=summary,
            start_chapter_index=chapter_index or None,
            status="open",
            memory_metadata={"provenance": "agent_inferred", "source": "track_plotline"},
        )
        ctx.db.add(mem)
        ctx.db.commit()
        return ToolResult.ok({
            "action": "opened",
            "id": mem.id,
            "title": title,
            "status": "open",
        })

    elif action == "close":
        if not title:
            return ToolResult.fail("close 操作需要 title 参数。")
        mem = (
            ctx.db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == ctx.project_id,
                LongformMemory.memory_type == "plotline",
                LongformMemory.scope_key == title,
                LongformMemory.status == "open",
            )
            .first()
        )
        if not mem:
            return ToolResult.fail(f"未找到开放的情节线「{title}」。")
        mem.status = "closed"
        mem.end_chapter_index = chapter_index or None
        ctx.db.commit()
        return ToolResult.ok({
            "action": "closed",
            "id": mem.id,
            "title": title,
            "status": "closed",
        })

    elif action == "query":
        query = ctx.db.query(LongformMemory).filter(
            LongformMemory.project_id == ctx.project_id,
            LongformMemory.memory_type == "plotline",
        )
        if title:
            query = query.filter(LongformMemory.scope_key == title)
        memories = query.order_by(LongformMemory.created_at.desc()).all()
        return ToolResult.ok({
            "action": "query_result",
            "plotlines": [
                {
                    "id": m.id,
                    "title": m.title,
                    "summary": m.summary,
                    "status": m.status,
                    "start_chapter": m.start_chapter_index,
                    "end_chapter": m.end_chapter_index,
                }
                for m in memories
            ],
        })

    return ToolResult.fail(f"未知操作：{action}，支持 open/close/query。")


@tool(
    registry=registry,
    name="query_memory",
    description=(
        "查询跨章节的长期记忆：按类型和关键字检索。"
        "【上下文注入上限】每次 LLM 调用最多使用本工具 1 次，返回最多 5 条记忆。"
        "推荐用法：1) 写作前用 memory_type='arc_summary' 回顾已完成弧线摘要（上限 3 条）；"
        "2) 用 memory_type='plotline' 检查开放情节线（上限 5 条）；"
        "3) 用 keyword 搜索特定人物/地点（上限 3 条）。"
        "注意每条 memory 携带 provenance 字段：author_explicit=作者显式设定（可信度高），agent_inferred=Agent 推理（可信度低）。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "memory_type": {
                "type": "string",
                "enum": ["plotline", "entity_state", "arc_summary", "all"],
                "description": "记忆类型。弧线摘要用 arc_summary",
            },
            "keyword": {"type": "string", "description": "搜索关键字（标题或内容）"},
            "limit": {"type": "integer", "description": "最多返回条数（默认 5，上限 10）", "default": 5},
            "provenance": {"type": "string", "enum": ["author_explicit", "agent_inferred", "all"], "description": "过滤来源", "default": "all"},
        },
    },
)
async def query_memory(ctx: ToolContext, memory_type: str = "all", keyword: str = "", limit: int = 5, provenance: str = "all") -> ToolResult:
    # Enforce injection cap (P0: Constrained Context Injection)
    effective_limit = min(limit, 10)
    query = ctx.db.query(LongformMemory).filter(
        LongformMemory.project_id == ctx.project_id,
    )
    if memory_type != "all":
        query = query.filter(LongformMemory.memory_type == memory_type)
    if provenance != "all":
        query = query.filter(LongformMemory.memory_metadata["provenance"].as_string() == provenance)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (LongformMemory.scope_key.like(like)) |
            (LongformMemory.title.like(like)) |
            (LongformMemory.summary.like(like))
        )
    memories = query.order_by(LongformMemory.updated_at.desc()).limit(effective_limit).all()

    result = {
        "memories": [
            {
                "id": m.id,
                "type": m.memory_type,
                "key": m.scope_key,
                "title": m.title,
                "summary": m.summary,
                "status": m.status,
                "provenance": (m.memory_metadata or {}).get("provenance", "agent_inferred"),
                "chapter_range": {
                    "start": m.start_chapter_index,
                    "end": m.end_chapter_index,
                },
            }
            for m in memories
        ],
        "total": len(memories),
        "injection_limit": {
            "returned": len(memories),
            "max_per_call": effective_limit,
            "guideline": (
                "上下文注入总上限: arc_summary ≤3条 + plotline ≤5条 + 实体/杂项 ≤3条。"
                "请根据当前写作阶段筛选最相关的记忆，不要全部注入。"
                "author_explicit 条目可信度更高，agent_inferred 条目需交叉验证。"
            ),
        },
    }

    # 2. Embedding fallback: SQL 无结果时用语义检索
    if not memories and keyword:
        try:
            retrieval = search_retrieval(
                ctx.db, ctx.project_id, keyword,
                limit=limit, max_chapter_index=None,
            )
            items = retrieval.get("items", [])
            result["embedding_results"] = [
                {
                    "source_type": i.get("source_type"),
                    "title": i.get("title"),
                    "chapter_index": i.get("chapter_index"),
                    "excerpt": (i.get("snippet") or "")[:300],
                    "score": i.get("score"),
                }
                for i in items[:limit]
            ]
            result["embedding_total"] = len(items)
        except Exception:
            result["embedding_error"] = "语义检索不可用"

    return ToolResult.ok(result)


# ── M5.1: Story Arc Planning ──


@tool(
    registry=registry,
    name="plan_arc",
    description=(
        "管理故事弧线，支持三种操作："
        "define=创建新弧线（需title/start_chapter/end_chapter/summary），"
        "progress=查询当前活跃弧线的进度（第X/Y章，剩余Z章），"
        "list=列出所有弧线。"
        "用于长程规划：在开始写作前定义弧线，写作过程中查询进度，弧线结束前提前规划下一弧线。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["define", "progress", "list"],
                "description": "操作：定义弧线、查询进度、列出弧线",
            },
            "title": {"type": "string", "description": "弧线标题，如「第一卷·迷雾初现」"},
            "summary": {"type": "string", "description": "弧线概要"},
            "start_chapter": {"type": "integer", "description": "弧线起始章节"},
            "end_chapter": {"type": "integer", "description": "弧线结束章节"},
        },
        "required": ["action"],
    },
)
async def plan_arc(
    ctx: ToolContext,
    action: str,
    title: str = "",
    summary: str = "",
    start_chapter: int = 0,
    end_chapter: int = 0,
) -> ToolResult:
    if action == "define":
        if not title or end_chapter < 1:
            return ToolResult.fail("define 操作需要 title 和 end_chapter（≥1）。")
        if start_chapter < 1:
            start_chapter = 1
        # Deactivate any currently active arc + auto-generate arc_summary
        active = (
            ctx.db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == ctx.project_id,
                LongformMemory.memory_type == "story_arc",
                LongformMemory.status == "active",
            )
            .all()
        )
        from app.models import ChapterContent
        for a in active:
            a.status = "completed"
            # Auto-generate arc_summary (fix: was only in progress, now also on define)
            chs = (
                ctx.db.query(ChapterContent)
                .filter(
                    ChapterContent.project_id == ctx.project_id,
                    ChapterContent.chapter_index >= (a.start_chapter_index or 1),
                    ChapterContent.chapter_index <= (a.end_chapter_index or 1),
                )
                .order_by(ChapterContent.chapter_index.asc())
                .all()
            )
            ch_titles = ", ".join(c.title for c in chs if c.title) or "(无标题)"
            arc_summary_text = (
                f"弧线「{a.title}」完成。"
                f"章节跨度: Ch{a.start_chapter_index}-{a.end_chapter_index}。"
                f"包含章节: {ch_titles}。"
                f"弧线概要: {a.summary or '(无)'}"
            )
            existing = (
                ctx.db.query(LongformMemory)
                .filter(
                    LongformMemory.project_id == ctx.project_id,
                    LongformMemory.memory_type == "arc_summary",
                    LongformMemory.scope_key == (a.title or f"arc_{a.id}"),
                )
                .first()
            )
            if not existing:
                ctx.db.add(LongformMemory(
                    project_id=ctx.project_id,
                    memory_type="arc_summary",
                    scope_key=a.title or f"arc_{a.id}",
                    title=f"弧线摘要: {a.title}",
                    summary=arc_summary_text,
                    start_chapter_index=a.start_chapter_index,
                    end_chapter_index=a.end_chapter_index,
                    status="completed",
                    memory_metadata={"provenance": "agent_inferred", "source": "arc_consolidation_auto"},
                ))
        # Create new arc
        arc = LongformMemory(
            project_id=ctx.project_id,
            memory_type="story_arc",
            scope_key=title,
            title=title,
            summary=summary or f"{start_chapter}-{end_chapter}章弧线",
            start_chapter_index=start_chapter,
            end_chapter_index=end_chapter,
            status="active",
            memory_metadata={"provenance": "author_explicit", "source": "plan_arc"},
        )
        ctx.db.add(arc)
        ctx.db.commit()
        return ToolResult.ok({
            "action": "defined",
            "title": title,
            "span": f"Ch{start_chapter} → Ch{end_chapter}",
            "total_chapters": end_chapter - start_chapter + 1,
            "status": "active",
            "tip": f"弧线「{title}」已激活。请在写作过程中定期调用 plan_arc progress 查看进度。弧线结束前 3 章请提前规划下一弧线。",
        })

    elif action == "progress":
        active_arc = (
            ctx.db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == ctx.project_id,
                LongformMemory.memory_type == "story_arc",
                LongformMemory.status == "active",
            )
            .first()
        )
        if not active_arc:
            return ToolResult.ok({
                "action": "progress",
                "status": "no_active_arc",
                "tip": "当前无活跃弧线。请用 plan_arc define 创建一个新弧线来规划后续章节。",
            })
        # Count existing chapters in the arc range
        from app.models import ChapterContent
        written = (
            ctx.db.query(ChapterContent)
            .filter(
                ChapterContent.project_id == ctx.project_id,
                ChapterContent.chapter_index >= (active_arc.start_chapter_index or 1),
                ChapterContent.chapter_index <= (active_arc.end_chapter_index or 1),
            )
            .count()
        )
        total = (active_arc.end_chapter_index or 1) - (active_arc.start_chapter_index or 1) + 1
        remaining = max(0, total - written)
        pct = round(written / total * 100) if total > 0 else 0
        near_end = remaining <= 3 and remaining > 0

        result = {
            "action": "progress",
            "arc_title": active_arc.title,
            "span": f"Ch{active_arc.start_chapter_index} → Ch{active_arc.end_chapter_index}",
            "written": written,
            "total": total,
            "remaining": remaining,
            "percent": pct,
        }
        if near_end:
            result["warning"] = (
                f"弧线「{active_arc.title}」即将结束（还剩 {remaining} 章）。"
                f"请尽快用 plan_arc define 规划下一弧线，避免故事失去方向。"
            )
        elif remaining <= 0:
            # ── Arc Memory Consolidation (openclaw Dreaming System analogue) ──
            # 弧线完成时自动写入摘要到 LongformMemory，供后续弧线召回
            active_arc.status = "completed"
            # Collect chapter titles in this arc for summary
            from app.models import ChapterContent
            chs = (
                ctx.db.query(ChapterContent)
                .filter(
                    ChapterContent.project_id == ctx.project_id,
                    ChapterContent.chapter_index >= (active_arc.start_chapter_index or 1),
                    ChapterContent.chapter_index <= (active_arc.end_chapter_index or 1),
                )
                .order_by(ChapterContent.chapter_index.asc())
                .all()
            )
            ch_titles = ", ".join(c.title for c in chs if c.title) or "(无标题)"
            arc_summary = (
                f"弧线「{active_arc.title}」完成。"
                f"章节跨度: Ch{active_arc.start_chapter_index}-{active_arc.end_chapter_index}。"
                f"包含章节: {ch_titles}。"
                f"弧线概要: {active_arc.summary or '(无)'}"
            )
            summary_mem = LongformMemory(
                project_id=ctx.project_id,
                memory_type="arc_summary",
                scope_key=active_arc.title or f"arc_{active_arc.id}",
                title=f"弧线摘要: {active_arc.title}",
                summary=arc_summary,
                start_chapter_index=active_arc.start_chapter_index,
                end_chapter_index=active_arc.end_chapter_index,
                status="completed",
                memory_metadata={"provenance": "agent_inferred", "source": "arc_consolidation"},
            )
            ctx.db.add(summary_mem)
            ctx.db.commit()
            result["arc_consolidated"] = True
            result["arc_summary"] = arc_summary
            result["warning"] = (
                f"弧线「{active_arc.title}」已完成并已巩固记忆（arc_summary）。"
                f"请立即用 plan_arc define 规划下一弧线。"
                f"写下一弧线前，可用 query_memory type=arc_summary 回顾已完成弧线的摘要。"
            )
        else:
            result["hint"] = (
                f"还有 {remaining} 章完成当前弧线。继续按大纲推进。"
            )
        return ToolResult.ok(result)

    elif action == "list":
        arcs = (
            ctx.db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == ctx.project_id,
                LongformMemory.memory_type == "story_arc",
            )
            .order_by(LongformMemory.start_chapter_index.asc())
            .all()
        )
        if not arcs:
            return ToolResult.ok({"action": "list", "arcs": [], "tip": "尚未定义任何弧线。"})
        return ToolResult.ok({
            "action": "list",
            "arcs": [
                {
                    "title": a.title,
                    "span": f"Ch{a.start_chapter_index} → Ch{a.end_chapter_index}",
                    "status": a.status,
                    "summary": a.summary,
                }
                for a in arcs
            ],
        })

    return ToolResult.fail(f"未知操作：{action}，支持 define/progress/list。")


# ── Memory Tree: 层级摘要树 (openhuman Memory Tree pattern) ──


@tool(
    registry=registry,
    name="memory_tree",
    description=(
        "查看项目的层级记忆树结构（project → arc → chapter → detail）。"
        "每层显示子节点数量和摘要信息。用于了解项目整体记忆组织、"
        "发现哪些弧线/章节缺少记忆覆盖、定位记忆空白区域。"
        "类比 openhuman 的 root→year→month→day 层级树，novelv3 映射为 project→arc→chapter→plotline。"
    ),
    permission="read",
    parameters={
        "type": "object",
        "properties": {
            "detail_level": {
                "type": "string",
                "enum": ["overview", "arcs", "chapters", "full"],
                "description": "详细程度：overview=总览，arcs=弧线级，chapters=章节级，full=完整树",
                "default": "overview",
            },
        },
    },
)
async def memory_tree(ctx: ToolContext, detail_level: str = "overview") -> ToolResult:
    from app.models import ChapterContent

    # Level 0: Project root
    total_chapters = (
        ctx.db.query(ChapterContent)
        .filter(ChapterContent.project_id == ctx.project_id)
        .count()
    )
    total_memories = (
        ctx.db.query(LongformMemory)
        .filter(LongformMemory.project_id == ctx.project_id)
        .count()
    )
    tree = {
        "project": {
            "id": ctx.project_id,
            "total_chapters": total_chapters,
            "total_memories": total_memories,
            "memory_density": round(total_memories / max(1, total_chapters), 1) if total_chapters > 0 else 0,
        },
    }

    # Level 1: Arcs
    arcs = (
        ctx.db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == ctx.project_id,
            LongformMemory.memory_type == "story_arc",
        )
        .order_by(LongformMemory.start_chapter_index.asc())
        .all()
    )
    tree["arcs"] = []
    for arc in arcs:
        arc_node = {
            "title": arc.title,
            "span": f"Ch{arc.start_chapter_index}-{arc.end_chapter_index}",
            "status": arc.status,
            "chapters_written": (
                ctx.db.query(ChapterContent)
                .filter(
                    ChapterContent.project_id == ctx.project_id,
                    ChapterContent.chapter_index >= (arc.start_chapter_index or 1),
                    ChapterContent.chapter_index <= (arc.end_chapter_index or 1),
                )
                .count()
            ),
        }

        if detail_level in ("chapters", "full"):
            # Level 2: Chapters within arc
            chapters = (
                ctx.db.query(ChapterContent)
                .filter(
                    ChapterContent.project_id == ctx.project_id,
                    ChapterContent.chapter_index >= (arc.start_chapter_index or 1),
                    ChapterContent.chapter_index <= (arc.end_chapter_index or 1),
                )
                .order_by(ChapterContent.chapter_index.asc())
                .all()
            )
            arc_node["chapters"] = []
            for ch in chapters:
                ch_node = {
                    "index": ch.chapter_index,
                    "title": ch.title or f"Ch{ch.chapter_index}",
                    "word_count": len(ch.content) if ch.content else 0,
                }

                if detail_level == "full":
                    # Level 3: Memories attached to this chapter
                    ch_mems = (
                        ctx.db.query(LongformMemory)
                        .filter(
                            LongformMemory.project_id == ctx.project_id,
                            LongformMemory.memory_type.in_(["plotline", "entity_state"]),
                            LongformMemory.start_chapter_index <= ch.chapter_index,
                        )
                        .all()
                    )
                    # Filter: memory was active during this chapter
                    relevant = [
                        m for m in ch_mems
                        if (m.end_chapter_index or 999) >= ch.chapter_index
                    ]
                    ch_node["active_memories"] = len(relevant)
                    ch_node["memory_types"] = list(set(m.memory_type for m in relevant))

                arc_node["chapters"].append(ch_node)

        tree["arcs"].append(arc_node)

    # Memory coverage analysis
    covered_chapters = set()
    for arc in arcs:
        for ch_idx in range(arc.start_chapter_index or 1, (arc.end_chapter_index or 1) + 1):
            covered_chapters.add(ch_idx)
    uncovered = [i for i in range(1, total_chapters + 1) if i not in covered_chapters]

    tree["coverage"] = {
        "arcs_defined": len(arcs),
        "chapters_covered_by_arcs": len(covered_chapters),
        "chapters_uncovered": len(uncovered),
        "uncovered_chapters": uncovered[:10] if len(uncovered) <= 10 else uncovered[:10] + [f"...and {len(uncovered)-10} more"],
        "status": (
            "full_coverage" if len(uncovered) == 0
            else "partial_coverage" if len(uncovered) < total_chapters * 0.3
            else "low_coverage"
        ),
    }

    # Summary (like OpenHuman's "folded" parent node summaries)
    summary_parts = [f"项目共 {total_chapters} 章, {total_memories} 条记忆, {len(arcs)} 条弧线。"]
    if arcs:
        active = [a for a in arcs if a.status == "active"]
        completed = [a for a in arcs if a.status == "completed"]
        if active:
            summary_parts.append(f"活跃弧线: {active[0].title} ({active[0].start_chapter_index}-{active[0].end_chapter_index})。")
        if completed:
            summary_parts.append(f"已完成 {len(completed)} 条弧线。")
    if uncovered:
        summary_parts.append(f"⚠ {len(uncovered)} 章未被弧线覆盖: {uncovered[:5]}{'...' if len(uncovered)>5 else ''}。")
    if total_chapters > 0 and total_memories / total_chapters < 1:
        summary_parts.append(f"记忆密度偏低 ({tree['project']['memory_density']}/章)，建议增加 track_plotline 调用。")

    tree["summary"] = " ".join(summary_parts)

    return ToolResult.ok(tree)
