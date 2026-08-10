"""记忆服务（arch-refactor：从旧 app/tools/memory.py handler 提取，工具描述与业务分离）。

服务函数签名 (db, project_id, ...) → dict；业务错误抛 MemoryServiceError，
由工具层转为结构化 ToolResult。行为与旧 handler 一致（200 章实验验证过的逻辑）。
"""
from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import ChapterContent, LongformMemory
from domain.memory.longform_memory import get_or_create_longform_memory
from domain.retrieval.athena_retrieval import search_retrieval

_PLOTLINE_TITLE_MAX = 60
_PLOTLINE_TITLE_TEMPLATE = "标题格式建议：核心冲突关键词，如「林舟身世之谜」；避免含章节序号。"
_PLOTLINE_STALE_AFTER = 30
_CHAPTER_REF = re.compile(r"第\s*\d+\s*[章卷部回]")

# 每通道注入配额（openhuman 多通道召回配额，特化适配网文记忆类型）：
# 混合查询时每通道硬上限，防止单通道刷屏挤占其他通道。
# 原 guideline 只是提示语（模型自觉遵守），现为代码强制。
_CHANNEL_LIMITS: dict[str, int] = {"arc_summary": 3, "plotline": 5}
_DEFAULT_CHANNEL_LIMIT = 3


def _channel_limit(memory_type: str) -> int:
    return _CHANNEL_LIMITS.get(memory_type, _DEFAULT_CHANNEL_LIMIT)


def _channel_limits_desc() -> str:
    """guideline 提示语从常量动态生成（code-review #15：消除配额数字三处拷贝的漂移）。"""
    parts = [f"{k} ≤{v}条" for k, v in _CHANNEL_LIMITS.items()]
    parts.append(f"实体/杂项 ≤{_DEFAULT_CHANNEL_LIMIT}条")
    return " + ".join(parts)


def _cap_by_channel(memories: list, global_limit: int) -> list:
    """按通道配额截断（保持输入排序：更新时间倒序 + author_explicit 优先）。"""
    counts: dict[str, int] = {}
    capped: list = []
    for m in memories:
        ch = m.memory_type
        if counts.get(ch, 0) >= _channel_limit(ch):
            continue
        counts[ch] = counts.get(ch, 0) + 1
        capped.append(m)
        if len(capped) >= global_limit:
            break
    return capped


class MemoryServiceError(Exception):
    """记忆服务业务错误（工具层转为 ToolResult.fail）。"""


def _open_plotlines_containing(db: Session, project_id: str, items: list[str]) -> list[str]:
    if not items:
        return []
    result: list[str] = []
    for item in items:
        m = (
            db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == project_id,
                LongformMemory.memory_type == "plotline",
                LongformMemory.status == "open",
                LongformMemory.scope_key.like(f"%{item}%"),
            )
            .first()
        )
        if m is not None:
            result.append(m.title)
    return result


# ── track_plotline ──


def track_plotline(
    db: Session,
    project_id: str,
    action: str,
    title: str = "",
    summary: str = "",
    chapter_index: int = 0,
) -> dict:
    if action == "open":
        if not title:
            raise MemoryServiceError("open 操作需要 title 参数。")
        if len(title) > _PLOTLINE_TITLE_MAX:
            raise MemoryServiceError(
                f"情节线标题过长（{len(title)} 字符，上限 {_PLOTLINE_TITLE_MAX}）。{_PLOTLINE_TITLE_TEMPLATE}"
            )
        if _CHAPTER_REF.search(title):
            raise MemoryServiceError(
                "情节线标题不应携带章节/卷/部序号（如「第139章线（第二部）」），否则后续检索必然失败。"
                f"{_PLOTLINE_TITLE_TEMPLATE}"
            )
        existing = get_or_create_longform_memory(
            db, project_id, "plotline", title,
            defaults={
                "title": title,
                "summary": summary,
                "start_chapter_index": chapter_index or None,
                "status": "open",
                "memory_metadata": {"provenance": "agent_inferred", "source": "track_plotline"},
            },
        )
        if existing.id is None:
            db.commit()
            return {"action": "opened", "id": existing.id, "title": title, "status": "open"}
        if existing.status == "open":
            return {"action": "already_exists", "id": existing.id, "title": title, "status": "open"}
        existing.status = "open"
        existing.summary = summary or existing.summary
        existing.start_chapter_index = chapter_index or existing.start_chapter_index
        existing.end_chapter_index = None
        db.commit()
        return {"action": "reopened", "id": existing.id, "title": title, "status": "open"}

    if action == "close":
        if not title:
            raise MemoryServiceError("close 操作需要 title 参数。")
        mem = (
            db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == project_id,
                LongformMemory.memory_type == "plotline",
                LongformMemory.scope_key == title,
                LongformMemory.status == "open",
            )
            .first()
        )
        if not mem:
            raise MemoryServiceError(f"未找到开放的情节线「{title}」。")
        mem.status = "closed"
        mem.end_chapter_index = chapter_index or None
        db.commit()
        return {"action": "closed", "id": mem.id, "title": title, "status": "closed"}

    if action == "query":
        base = db.query(LongformMemory).filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "plotline",
        )
        if title:
            memories = (
                base.filter(LongformMemory.scope_key.like(f"%{title}%"))
                .order_by(LongformMemory.created_at.desc())
                .all()
            )
        else:
            memories = base.order_by(LongformMemory.created_at.desc()).all()
        result: dict = {
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
        }
        if memories:
            latest_row = (
                db.query(ChapterContent.chapter_index)
                .filter(ChapterContent.project_id == project_id)
                .order_by(ChapterContent.chapter_index.desc())
                .first()
            )
            latest_index = latest_row[0] if latest_row else 0
            stale_open: list[str] = []
            for item, m in zip(result["plotlines"], memories, strict=False):
                if (
                    m.status == "open"
                    and m.start_chapter_index is not None
                    and latest_index - m.start_chapter_index > _PLOTLINE_STALE_AFTER
                ):
                    item["stale"] = True
                    item["age_chapters"] = latest_index - m.start_chapter_index
                    stale_open.append(f"「{m.title}」(起始于第{m.start_chapter_index}章)")
            if stale_open:
                result["stale_warning"] = (
                    f"以下伏笔已开放超过 {_PLOTLINE_STALE_AFTER} 章：{'、'.join(stale_open)}。"
                    f"请在本卷收束前回收，或显式闭环。"
                )
        if title and not memories:
            fallback_row = (
                base.filter(LongformMemory.status == "open")
                .order_by(LongformMemory.created_at.desc())
                .first()
            )
            if fallback_row is not None:
                result["fallback"] = True
                result["fallback_note"] = (
                    f"未找到标题匹配「{title}」的情节线，已回退最近创建的开放情节线「{fallback_row.title}」。"
                )
                result["plotlines"] = [
                    {
                        "id": fallback_row.id,
                        "title": fallback_row.title,
                        "summary": fallback_row.summary,
                        "status": fallback_row.status,
                        "start_chapter": fallback_row.start_chapter_index,
                        "end_chapter": fallback_row.end_chapter_index,
                    }
                ]
            else:
                result["fallback"] = True
                result["fallback_note"] = f"未找到标题匹配「{title}」的情节线，且无开放的备选情节线。"
        return result

    raise MemoryServiceError(f"未知操作：{action}，支持 open/close/query。")


# ── query_memory ──


def query_memory(
    db: Session,
    project_id: str,
    memory_type: str = "all",
    keyword: str = "",
    limit: int = 5,
    provenance: str = "all",
) -> dict:
    effective_limit = min(limit, 10)
    query = db.query(LongformMemory).filter(LongformMemory.project_id == project_id)
    # 内部日志类型与归档条目不进记忆查询（code-review #4/#6：introspect_log 空行
    # 曾挤占通道配额；archived 经验按 09 定稿「不再注入」，与快照路径语义一致）
    query = query.filter(
        LongformMemory.memory_type != "introspect_log",
        LongformMemory.status != "archived",
    )
    if memory_type != "all":
        query = query.filter(LongformMemory.memory_type == memory_type)
    if provenance != "all":
        query = query.filter(LongformMemory.memory_metadata["provenance"].as_string() == provenance)
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(
            (LongformMemory.scope_key.like(like))
            | (LongformMemory.title.like(like))
            | (LongformMemory.summary.like(like))
        )
    if memory_type == "all":
        # 每通道独立预取（code-review #7：全局预取窗口下低频通道可能零代表，
        # 单通道 flood 时其他通道在窗口内一条不剩）
        type_rows = (
            db.query(LongformMemory.memory_type)
            .filter(LongformMemory.project_id == project_id)
            .distinct()
            .all()
        )
        memories: list = []
        for (t,) in type_rows:
            if t == "introspect_log":
                continue
            memories.extend(
                query.filter(LongformMemory.memory_type == t)
                .order_by(LongformMemory.updated_at.desc())
                .limit(_channel_limit(t) * 2)
                .all()
            )
    else:
        memories = (
            query.order_by(LongformMemory.updated_at.desc())
            .limit(effective_limit * 3)
            .all()
        )
    memories.sort(
        key=lambda m: (0 if (m.memory_metadata or {}).get("provenance") == "author_explicit" else 1)
    )
    # 通道配额强制（openhuman）：混合查询按通道硬截断（各通道上限见 _CHANNEL_LIMITS）
    memories = _cap_by_channel(memories, effective_limit) if memory_type == "all" else memories[:effective_limit]

    result: dict = {
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
            "channel_limits": dict(_CHANNEL_LIMITS) if memory_type == "all" else None,
            "guideline": (
                "上下文注入配额已由服务端强制（混合查询时每通道硬上限: "
                f"{_channel_limits_desc()}；"
                "单类型查询按 limit 返回，请自行筛选最相关条目）。"
                "author_explicit 条目可信度更高，agent_inferred 条目需交叉验证。"
            ),
        },
    }

    if not memories and keyword:
        try:
            retrieval = search_retrieval(
                db, project_id, keyword,
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

    return result


# ── plan_arc ──


def _close_active_arcs(db: Session, project_id: str) -> None:
    """关闭所有活跃弧线并生成 arc_summary（define 新弧线时的前置动作）。"""
    active = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "story_arc",
            LongformMemory.status == "active",
        )
        .all()
    )
    for a in active:
        a.status = "completed"
        chs = (
            db.query(ChapterContent)
            .filter(
                ChapterContent.project_id == project_id,
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
        mem = get_or_create_longform_memory(
            db, project_id, "arc_summary",
            a.title or f"arc_{a.id}",
            defaults={
                "title": f"弧线摘要: {a.title}",
                "summary": arc_summary_text,
                "start_chapter_index": a.start_chapter_index,
                "end_chapter_index": a.end_chapter_index,
                "status": "completed",
                "memory_metadata": {"provenance": "agent_inferred", "source": "arc_consolidation_auto"},
            },
        )
        # 同名弧线重复 define 时显式覆盖（get_or_create 命中已有键跳过 defaults，
        # 否则新摘要永不落库——code-review #13；跨度字段一并覆盖——二轮 R9）
        mem.summary = arc_summary_text
        mem.title = f"弧线摘要: {a.title}"
        mem.start_chapter_index = a.start_chapter_index
        mem.end_chapter_index = a.end_chapter_index
        mem.status = "completed"


def plan_arc(
    db: Session,
    project_id: str,
    action: str,
    title: str = "",
    summary: str = "",
    start_chapter: int = 0,
    end_chapter: int = 0,
    must_resolve: list[str] | None = None,
    relation_to_previous: str = "",
) -> dict:
    if action == "define":
        if not title or end_chapter < 1:
            raise MemoryServiceError("define 操作需要 title 和 end_chapter（≥1）。")
        if start_chapter < 1:
            start_chapter = 1
        _close_active_arcs(db, project_id)
        arc = get_or_create_longform_memory(
            db, project_id, "story_arc", title,
            defaults={
                "title": title,
                "summary": summary or f"{start_chapter}-{end_chapter}章弧线",
                "start_chapter_index": start_chapter,
                "end_chapter_index": end_chapter,
                "status": "active",
                "memory_metadata": {"provenance": "author_explicit", "source": "plan_arc"},
            },
        )
        arc.summary = summary or arc.summary
        arc.start_chapter_index = start_chapter
        arc.end_chapter_index = end_chapter
        arc.status = "active"
        if must_resolve:
            meta = dict(arc.memory_metadata or {})
            meta["endgame"] = {"resolve_before": end_chapter, "must_resolve": list(must_resolve)}
            arc.memory_metadata = meta
        if relation_to_previous:
            meta = dict(arc.memory_metadata or {})
            meta["arc_relation"] = relation_to_previous
            arc.memory_metadata = meta
        db.commit()
        return {
            "action": "defined",
            "arc_id": arc.id,
            "title": title,
            "span": f"Ch{start_chapter} → Ch{end_chapter}",
            "status": "active",
        }

    if action == "progress":
        active_arc = (
            db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == project_id,
                LongformMemory.memory_type == "story_arc",
                LongformMemory.status == "active",
            )
            .first()
        )
        if not active_arc:
            return {
                "action": "progress",
                "status": "no_active_arc",
                "tip": "当前无活跃弧线。请用 plan_arc define 创建一个新弧线来规划后续章节。",
            }
        written = (
            db.query(ChapterContent)
            .filter(
                ChapterContent.project_id == project_id,
                ChapterContent.chapter_index >= (active_arc.start_chapter_index or 1),
                ChapterContent.chapter_index <= (active_arc.end_chapter_index or 1),
            )
            .count()
        )
        total = (active_arc.end_chapter_index or 1) - (active_arc.start_chapter_index or 1) + 1
        remaining = max(0, total - written)
        pct = round(written / total * 100) if total > 0 else 0
        near_end = remaining <= 3 and remaining > 0

        result: dict = {
            "action": "progress",
            "arc_title": active_arc.title,
            "span": f"Ch{active_arc.start_chapter_index} → Ch{active_arc.end_chapter_index}",
            "written": written,
            "total": total,
            "remaining": remaining,
            "percent": pct,
        }

        endgame = (active_arc.memory_metadata or {}).get("endgame")
        if not endgame:
            result["endgame_hint"] = (
                "本卷未设置收束约束（define 时可补 must_resolve 与收束章）。"
                "长卷易出现开线不收束，建议补设回收清单。"
            )
        if endgame:
            latest_row = (
                db.query(ChapterContent.chapter_index)
                .filter(ChapterContent.project_id == project_id)
                .order_by(ChapterContent.chapter_index.desc())
                .first()
            )
            latest_index = latest_row[0] if latest_row else 0
            resolve_before = int(endgame.get("resolve_before") or 0)
            remaining_to_end = max(0, resolve_before - latest_index)
            must_open = _open_plotlines_containing(db, project_id, endgame.get("must_resolve") or [])
            result["endgame_remaining"] = remaining_to_end
            result["must_resolve_open"] = must_open
            if must_open and remaining_to_end <= 5:
                result["endgame_warning"] = (
                    f"本卷剩余 {remaining_to_end} 章，以下伏笔必须在收束前回收："
                    f"{'、'.join(must_open)}。接近收束章，请优先回收开放线索，暂缓开新线，"
                    f"进入回收模式集中收束。"
                )

        if near_end:
            result["warning"] = (
                f"弧线「{active_arc.title}」即将结束（还剩 {remaining} 章）。"
                f"请尽快用 plan_arc define 规划下一弧线，避免故事失去方向。"
            )
        elif remaining <= 0:
            active_arc.status = "completed"
            chs = (
                db.query(ChapterContent)
                .filter(
                    ChapterContent.project_id == project_id,
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
            mem = get_or_create_longform_memory(
                db, project_id, "arc_summary",
                active_arc.title or f"arc_{active_arc.id}",
                defaults={
                    "title": f"弧线摘要: {active_arc.title}",
                    "summary": arc_summary,
                    "start_chapter_index": active_arc.start_chapter_index,
                    "end_chapter_index": active_arc.end_chapter_index,
                    "status": "completed",
                    "memory_metadata": {"provenance": "agent_inferred", "source": "arc_consolidation"},
                },
            )
            # 显式覆盖（同名弧线复用场景，code-review #13；跨度字段一并覆盖——二轮 R9）
            mem.summary = arc_summary
            mem.title = f"弧线摘要: {active_arc.title}"
            mem.start_chapter_index = active_arc.start_chapter_index
            mem.end_chapter_index = active_arc.end_chapter_index
            mem.status = "completed"
            db.commit()
            result["arc_consolidated"] = True
            result["arc_summary"] = arc_summary
            result["warning"] = (
                f"弧线「{active_arc.title}」已完成并已巩固记忆（arc_summary）。"
                f"请立即用 plan_arc define 规划下一弧线。"
                f"写下一弧线前，可用 query_memory type=arc_summary 回顾已完成弧线的摘要。"
            )
        else:
            result["hint"] = f"还有 {remaining} 章完成当前弧线。继续按大纲推进。"
        return result

    if action == "list":
        arcs = (
            db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == project_id,
                LongformMemory.memory_type == "story_arc",
            )
            .order_by(LongformMemory.start_chapter_index.asc())
            .all()
        )
        if not arcs:
            return {"action": "list", "arcs": [], "tip": "尚未定义任何弧线。"}
        return {
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
        }

    raise MemoryServiceError(f"未知操作：{action}，支持 define/progress/list。")


# ── 弧线内容级联摘要（openhuman 封箱聚合，B4）──

_ARC_AGGREGATE_SYSTEM_PROMPT = (
    "你是长篇小说的卷级摘要器。根据弧线的章节正文摘录，生成一段内容级联摘要"
    "（200 字以内）：弧线主线、关键事件推进、人物状态变化、当前遗留悬念。"
    "只描述弧线内已发生的事实，不预测后续情节，不使用 markdown。"
)


async def aggregate_arc_summary(
    db: Session,
    project_id: str,
    arc,
    *,
    provider,
) -> dict:
    """单条弧线的 LLM 内容级联摘要（openhuman 封箱聚合，特化：弧线=自然封箱单元）。

    已有 LLM 版（memory_metadata.aggregated=True）→ 跳过（幂等）；
    无章节/空输出 → 保持原标题清单版（fail-open，不覆盖）。
    """
    arc_summary = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "arc_summary",
            LongformMemory.scope_key == (arc.title or f"arc_{arc.id}"),
        )
        .first()
    )
    if arc_summary is not None and (arc_summary.memory_metadata or {}).get("aggregated"):
        return {"status": "skipped", "reason": "already_aggregated"}

    chapters = (
        db.query(ChapterContent)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index >= (arc.start_chapter_index or 1),
            ChapterContent.chapter_index <= (arc.end_chapter_index or 1),
        )
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    chapter_notes = [
        f"Ch{c.chapter_index}《{c.title}》：{(c.content or '')[:120]}…" for c in chapters[:15]
    ]
    if not chapter_notes:
        return {"status": "skipped", "reason": "no_chapters"}

    span = f"Ch{arc.start_chapter_index}-{arc.end_chapter_index}"
    user_prompt = (
        f"弧线「{arc.title}」({span})，概要：{arc.summary or '（无）'}。\n\n"
        f"章节摘录：\n" + "\n".join(chapter_notes)
    )
    try:
        response = await provider.complete(
            [
                {"role": "system", "content": _ARC_AGGREGATE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )
    except Exception:  # noqa: BLE001 - 聚合失败保持标题清单版（fail-open）
        return {"status": "failed", "reason": "provider_error"}
    text = (response.content or "").strip()
    if not text:
        return {"status": "failed", "reason": "empty_output"}

    if arc_summary is None:
        arc_summary = get_or_create_longform_memory(
            db, project_id, "arc_summary", arc.title or f"arc_{arc.id}",
            defaults={
                "title": f"弧线摘要: {arc.title}",
                "summary": text,
                "start_chapter_index": arc.start_chapter_index,
                "end_chapter_index": arc.end_chapter_index,
                "status": "completed",
                "memory_metadata": {"provenance": "agent_inferred", "source": "arc_aggregation_llm"},
            },
        )
    arc_summary.summary = text
    meta = dict(arc_summary.memory_metadata or {})
    meta["aggregated"] = True
    meta["source"] = "arc_aggregation_llm"
    arc_summary.memory_metadata = meta
    db.commit()
    return {"status": "aggregated", "arc": arc.title, "summary_len": len(text)}


async def aggregate_pending_arc_summaries(db: Session, project_id: str, *, provider) -> list[dict]:
    """批量聚合已完成但未 LLM 聚合的弧线（最近 3 条，最旧优先聚合）。

    触发点：章末自省路径（agent.py _introspect_after_send）顺带执行——
    弧线完成由 plan_arc 触发（模型调用），聚合最迟延迟一个 send。
    """
    completed = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == "story_arc",
            LongformMemory.status == "completed",
        )
        .order_by(LongformMemory.start_chapter_index.desc())
        .limit(3)
        .all()
    )
    results: list[dict] = []
    for arc in reversed(completed):  # 最旧的先聚合
        try:
            results.append(await aggregate_arc_summary(db, project_id, arc, provider=provider))
        except Exception:  # noqa: BLE001 - fail-open：单条失败不影响其余
            results.append({"status": "failed", "arc": arc.title})
    return results


# ── memory_tree ──


def memory_tree(db: Session, project_id: str, detail_level: str = "overview") -> dict:
    memories = (
        db.query(LongformMemory)
        .filter(LongformMemory.project_id == project_id)
        .order_by(LongformMemory.start_chapter_index.asc())
        .all()
    )
    chapters = (
        db.query(ChapterContent.chapter_index, ChapterContent.title)
        .filter(ChapterContent.project_id == project_id)
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )
    arcs = [m for m in memories if m.memory_type == "story_arc"]
    plotlines = [m for m in memories if m.memory_type == "plotline"]
    arc_chapters = [m for m in memories if m.memory_type == "arc"]
    chapter_mems = [m for m in memories if m.memory_type == "chapter"]

    tree: dict = {
        "project_id": project_id,
        "total_memories": len(memories),
        "chapters": len(chapters),
        "arcs": [
            {
                "title": a.title,
                "span": f"Ch{a.start_chapter_index}-{a.end_chapter_index}",
                "status": a.status,
                "children": {
                    "arc_memories": sum(1 for m in arc_chapters if (m.start_chapter_index or 0) >= (a.start_chapter_index or 0) and (m.end_chapter_index or 0) <= (a.end_chapter_index or 0)),
                    "chapter_memories": sum(1 for m in chapter_mems if (m.start_chapter_index or 0) >= (a.start_chapter_index or 0) and (m.end_chapter_index or 0) <= (a.end_chapter_index or 0)),
                },
            }
            for a in arcs
        ],
        "plotlines": {"open": sum(1 for p in plotlines if p.status == "open"), "closed": sum(1 for p in plotlines if p.status == "closed")},
    }

    if detail_level in ("chapters", "full"):
        tree["chapter_coverage"] = [
            {
                "chapter_index": c[0],
                "title": c[1],
                "has_memory": any(m.start_chapter_index == c[0] for m in chapter_mems),
            }
            for c in chapters
        ]
    if detail_level == "full":
        tree["memories"] = [
            {
                "type": m.memory_type,
                "key": m.scope_key,
                "status": m.status,
                "span": f"Ch{m.start_chapter_index}-{m.end_chapter_index}",
            }
            for m in memories
        ]
    return tree
