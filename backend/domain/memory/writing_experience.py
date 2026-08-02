"""per-book 自优化：章末自省 → 写作经验记忆（09 定稿实现）。

流程：每章 finalize / harness 回合结束后，自省 LLM 短调用（锚定章纲 + 负面采样）
→ 结构化输出（分类 + [{key, action, text}]）→ 信任度记账（new/reinforce/override +
惰性衰减 + 预算淘汰）→ 下一章快照【写作经验】段自动携带。

信任度语义（评审修正）：new=1，reinforce+1（LLM 判定同主题重复出现），
override 旧经验 -1 且新文本覆盖；30 章未强化 → -1；≤0 → archived。
作者入口：delete_experience / pin_experience（pinned 不衰减不淘汰）。

fail-open：自省 LLM 调用失败由调用方捕获（记日志），不阻塞写作流程。
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import LongformMemory

logger = logging.getLogger(__name__)

EXPERIENCE_TYPE = "writing_experience"
# 自省标记类型：普通列 scope_key 存 "chapter:{n}"（幂等判定不依赖 JSON 索引）
INTROSPECT_LOG_TYPE = "introspect_log"
# 自省分类轮转（每章自省一类，4 章一轮）
INTROSPECT_CATEGORIES = ("节奏", "文风", "设定运用", "教训")

_TRUST_INITIAL = 1
_STALE_AFTER_CHAPTERS = 30
_MAX_PER_CATEGORY = 20
_HIGH_TRUST_THRESHOLD = 3
_RECENT_INJECT_COUNT = 2
_HIGH_TRUST_INJECT_COUNT = 1
_TEXT_MAX_LEN = 60
_KEY_CANDIDATE_COUNT = 5
_ACTIVE = "current"
_ARCHIVED = "archived"

# 自省提示词纪律（评审护栏）：锚定章纲 + 负面采样；只记写作实践；设定事实不入库
_INTROSPECT_SYSTEM_PROMPT = (
    "你是本章的写作复盘者，帮助长篇网文作者积累写作经验。"
    "阅读本章正文与章纲，只输出写作实践层面的经验（节奏手段/文风手段/设定使用方式/过程教训）。"
    "纪律：1) 禁止记录情节内容类教训（如'不要写××情节'）；"
    "2) 设定事实不入经验库——'灵力消耗规则'这类设定只存在于设定卡，"
    "但'灵力消耗在战斗里自然带出效果好'这类呈现手法可以记录；"
    "3) 格式类问题已由规则检查覆盖，不要重复记录。"
    "必须进行负面采样：找出本章相对章纲的偏离与最失败之处。"
    "输出严格 JSON：{\"experiences\": [{\"key\": \"主题短键\", "
    "\"action\": \"new|reinforce|override\", \"text\": \"经验（≤60字）\"}]}。"
    "key 尽量复用下方提供的候选键（reinforce/override 必须命中候选键）；"
    "无匹配时新建 key（action=new）。经验不足可不输出（experiences 可为空数组）。"
)


class WritingExperienceError(Exception):
    """写作经验服务业务错误。"""


def _now() -> datetime:
    return datetime.now(UTC)


def _candidate_keys(db: Session, project_id: str, category: str, limit: int = _KEY_CANDIDATE_COUNT) -> list[str]:
    """该类目最近强化的经验键（自省提示词携带，防 key 漂移导致 override 永不生效）。"""
    rows = (
        db.query(LongformMemory.scope_key)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == EXPERIENCE_TYPE,
            LongformMemory.memory_metadata["category"].as_string() == category,
            LongformMemory.status == _ACTIVE,
        )
        .order_by(LongformMemory.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [r[0] for r in rows]


def _build_introspect_user_prompt(
    chapter_index: int,
    category: str,
    plan_context: str,
    chapter_text: str,
    review_reasons: str,
    candidate_keys: list[str],
) -> str:
    lines = [
        f"当前章节：第 {chapter_index} 章（自省分类：{category}）。",
        f"章纲/计划：{plan_context or '（无）'}",
        f"评审意见（若有）：{review_reasons or '（无）'}",
        f"已有经验键（优先复用）：{('、'.join(candidate_keys)) or '（无）'}",
        f"本章正文：\n{chapter_text[:6000]}",
    ]
    return "\n".join(lines)


def apply_experiences(
    db: Session,
    project_id: str,
    chapter_index: int,
    category: str,
    items: list[dict],
) -> dict:
    """信任度记账：new/reinforce/override + 惰性衰减 + 预算淘汰。可独立测试。

    items: [{"key": str, "action": "new|reinforce|override", "text": str}]
    """
    applied = {"new": 0, "reinforce": 0, "override": 0, "skipped": 0}

    # 惰性衰减（评审护栏：30 章未强化 → -1；≤0 → archived；pinned 豁免）
    _decay_stale(db, project_id, category, chapter_index)

    for item in items:
        key = str(item.get("key", "")).strip()
        action = str(item.get("action", "new")).strip()
        text = str(item.get("text", "")).strip()[: _TEXT_MAX_LEN * 2]
        if not key or not text:
            applied["skipped"] += 1
            continue
        entry = (
            db.query(LongformMemory)
            .filter(
                LongformMemory.project_id == project_id,
                LongformMemory.memory_type == EXPERIENCE_TYPE,
                LongformMemory.scope_key == key,
            )
            .first()
        )
        if entry is None:
            # 新建（new；显式 reinforce 但键不存在时也按 new 兜底）
            db.add(
                LongformMemory(
                    project_id=project_id,
                    memory_type=EXPERIENCE_TYPE,
                    scope_key=key,
                    title=f"[{category}] {key}",
                    summary=text,
                    start_chapter_index=chapter_index,
                    status=_ACTIVE,
                    memory_metadata={
                        "category": category,
                        "trust_score": _TRUST_INITIAL,
                        "last_reinforce_chapter_index": chapter_index,
                        "pinned": False,
                        "provenance": "agent_inferred",
                        "source_chapter": chapter_index,
                    },
                )
            )
            applied["new"] += 1
            continue
        meta = dict(entry.memory_metadata or {})
        trust = int(meta.get("trust_score", _TRUST_INITIAL))
        if action == "override":
            # 推翻：旧经验降权，新文本覆盖
            entry.summary = text
            entry.title = f"[{category}] {key}"
            meta["trust_score"] = max(0, trust - 1)
            meta["last_reinforce_chapter_index"] = chapter_index
            applied["override"] += 1
        else:  # reinforce（含 new 落到已存在键的情况）
            meta["trust_score"] = min(trust + 1, 99)
            entry.summary = text
            meta["last_reinforce_chapter_index"] = chapter_index
            applied["reinforce"] += 1
        meta["source_chapter"] = chapter_index
        entry.memory_metadata = meta
        entry.updated_at = _now()

    db.commit()

    # 预算淘汰（每类上限，按信任度淘汰最低，archived 不删除）
    _enforce_budget(db, project_id, category)
    return applied


def _decay_stale(db: Session, project_id: str, category: str, chapter_index: int) -> None:
    """惰性衰减：30 章未强化 → trust-1；≤0 → archived（pinned 豁免）。"""
    rows = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == EXPERIENCE_TYPE,
            LongformMemory.memory_metadata["category"].as_string() == category,
            LongformMemory.status == _ACTIVE,
        )
        .all()
    )
    for entry in rows:
        meta = dict(entry.memory_metadata or {})
        if meta.get("pinned"):
            continue
        last = int(meta.get("last_reinforce_chapter_index") or 0)
        trust = int(meta.get("trust_score", _TRUST_INITIAL))
        if last and chapter_index - last >= _STALE_AFTER_CHAPTERS:
            trust -= 1
            meta["trust_score"] = max(0, trust)
            meta["last_reinforce_chapter_index"] = chapter_index  # 衰减后重新计时
            if trust <= 0:
                entry.status = _ARCHIVED
            entry.memory_metadata = meta
            entry.updated_at = _now()


def _enforce_budget(db: Session, project_id: str, category: str) -> None:
    """预算：每类上限 _MAX_PER_CATEGORY 条，超限按信任度淘汰最低（archived）。"""
    rows = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == EXPERIENCE_TYPE,
            LongformMemory.memory_metadata["category"].as_string() == category,
            LongformMemory.status == _ACTIVE,
        )
        .all()
    )
    if len(rows) <= _MAX_PER_CATEGORY:
        return
    candidates = sorted(
        [r for r in rows if not (r.memory_metadata or {}).get("pinned")],
        key=lambda r: (int((r.memory_metadata or {}).get("trust_score", 0)), r.updated_at or _now()),
    )
    overflow = len(rows) - _MAX_PER_CATEGORY
    for entry in candidates[:overflow]:
        entry.status = _ARCHIVED
        entry.updated_at = _now()
    db.commit()


async def introspect_and_record(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    provider,
    plan_context: str = "",
    chapter_text: str = "",
    review_reasons: str = "",
) -> dict:
    """章末自省 + 记账（幂等：该章已自省过则跳过）。

    自省 LLM 调用失败抛 ProviderError 等异常——由调用方 fail-open 捕获。
    """
    # 幂等：该章已有自省标记 → 跳过（会话重启安全；不依赖 JSON 索引比较）
    log = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == INTROSPECT_LOG_TYPE,
            LongformMemory.scope_key == f"chapter:{chapter_index}",
        )
        .first()
    )
    if log is not None:
        return {"status": "skipped", "reason": "chapter_already_introspected"}

    category = INTROSPECT_CATEGORIES[(chapter_index - 1) % len(INTROSPECT_CATEGORIES)]
    candidate_keys = _candidate_keys(db, project_id, category)
    user_prompt = _build_introspect_user_prompt(
        chapter_index, category, plan_context, chapter_text, review_reasons, candidate_keys
    )
    response = await provider.complete(
        [
            {"role": "system", "content": _INTROSPECT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
    )
    items = _parse_introspect_output(response.content)
    applied = apply_experiences(db, project_id, chapter_index, category, items)
    # 自省完成标记（provider 调用已发生，无论解析结果；失败路径由调用方 fail-open 处理）
    db.add(
        LongformMemory(
            project_id=project_id,
            memory_type=INTROSPECT_LOG_TYPE,
            scope_key=f"chapter:{chapter_index}",
            title="",
            summary="",
            start_chapter_index=chapter_index,
            status="done",
            memory_metadata={"provenance": "agent_inferred", "source": "introspect_log"},
        )
    )
    db.commit()
    return {
        "status": "recorded",
        "category": category,
        "applied": applied,
        "chapter_index": chapter_index,
    }


def _parse_introspect_output(content: str) -> list[dict]:
    """解析自省 JSON 输出（容错：解析失败记录日志并返回空，不炸流程）。"""
    text = content.strip()
    try:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError("no json object")
        parsed = json.loads(text[start : end + 1])
    except (ValueError, json.JSONDecodeError):
        logger.warning("introspect output not parseable, dropped: %.100s", text)
        return []
    experiences = parsed.get("experiences") if isinstance(parsed, dict) else None
    if not isinstance(experiences, list):
        return []
    valid = []
    for item in experiences:
        if isinstance(item, dict) and item.get("key") and item.get("text"):
            valid.append(item)
    return valid


def experience_injection_items(
    db: Session,
    project_id: str,
    *,
    recent_n: int = _RECENT_INJECT_COUNT,
    high_trust_n: int = _HIGH_TRUST_INJECT_COUNT,
    high_trust_threshold: int = _HIGH_TRUST_THRESHOLD,
) -> list[dict]:
    """快照注入条目：最近 recent_n 条（按最近强化倒序）+ 高信任 high_trust_n 条（轮转）。

    高信任轮转：取 trust≥阈值中「最近强化距当前最远」的一条，避免同条连续注入。
    每条 text 截断 _TEXT_MAX_LEN；带章节锚点（如 Ch12 验证）。
    """
    rows = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == EXPERIENCE_TYPE,
            LongformMemory.status == _ACTIVE,
        )
        .order_by(
            LongformMemory.memory_metadata["last_reinforce_chapter_index"].as_string().desc(),
            LongformMemory.updated_at.desc(),
        )
        .all()
    )
    if not rows:
        return []
    recent = rows[:recent_n]
    high_trust = [r for r in rows if int((r.memory_metadata or {}).get("trust_score", 0)) >= high_trust_threshold]
    selected = list(recent)
    if high_trust_n and high_trust:
        # 轮转：取最近强化距当前最远的（按 updated_at 升序第一个不在 recent 里的）
        for r in sorted(high_trust, key=lambda r: r.updated_at or _now()):
            if r not in selected:
                selected.append(r)
                if len(selected) >= recent_n + high_trust_n:
                    break
    items = []
    for r in selected[: recent_n + high_trust_n]:
        meta = r.memory_metadata or {}
        last = int(meta.get("last_reinforce_chapter_index") or 0)
        anchor = f"Ch{last}验证" if last else "经验"
        text = (r.summary or r.title or "")[:_TEXT_MAX_LEN]
        items.append({"anchor": anchor, "text": text})
    return items


# ── 作者否决入口（Phase 2 API 接线前的 domain 函数）──


def delete_experience(db: Session, project_id: str, key: str) -> dict:
    """作者否决：物理删除指定经验。"""
    entry = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == EXPERIENCE_TYPE,
            LongformMemory.scope_key == key,
        )
        .first()
    )
    if entry is None:
        raise WritingExperienceError(f"未找到写作经验「{key}」")
    db.delete(entry)
    db.commit()
    return {"deleted": True, "key": key}


def pin_experience(db: Session, project_id: str, key: str, pinned: bool) -> dict:
    """作者钉住/解除：pinned 经验不衰减、不淘汰。"""
    entry = (
        db.query(LongformMemory)
        .filter(
            LongformMemory.project_id == project_id,
            LongformMemory.memory_type == EXPERIENCE_TYPE,
            LongformMemory.scope_key == key,
        )
        .first()
    )
    if entry is None:
        raise WritingExperienceError(f"未找到写作经验「{key}」")
    meta = dict(entry.memory_metadata or {})
    meta["pinned"] = bool(pinned)
    entry.memory_metadata = meta
    entry.updated_at = _now()
    db.commit()
    return {"key": key, "pinned": bool(pinned)}
