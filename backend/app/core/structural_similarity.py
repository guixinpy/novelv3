"""结构级重复检测纯函数（T5）。

检测「换名城」式模板循环（200 章评审实证：沈水镇→未醒之城→更下游城→源头城，
每座城=名字+树/针脚/水+一次性点破者，结构完全雷同）：
1. 标题重复（「渡到底的是心」×3、「最初是谁」×3）
2. 结尾主题词指纹雷同（ch160-201「最初的名字/来处/轮廓/成形」式哲学套话循环）

确定性规则，无 NLP 依赖；只提示不强制。
"""
from __future__ import annotations

import re

_TITLE_MIN_CHARS = 4  # 占位符标题（如「第31章」）不参与
_TAIL_CHARS = 120     # 结尾指纹窗口
_TOPIC_HITS_MIN = 2   # 每章结尾命中主题词 ≥2 个 = 模板结尾
_CLUSTER_MIN = 3      # 模板结尾 ≥3 章 = 结构重复

# 200 章实证主题词（第二部高频抽象循环词）
_TOPIC_WORDS = (
    "最初", "来处", "名字", "极静", "极稳", "落下", "守着",
    "望着", "轮廓", "成形", "更前", "更早", "更初", "水光", "那道",
)

_PUNCT_RE = re.compile(r"[-，。！？、；：""''（）·_]+")


def _norm(text: str) -> str:
    return _PUNCT_RE.sub("", text or "")


def detect_structure_repeats(chapters: list[dict]) -> list[dict]:
    """输入 [{index, title, content}]，输出 issues（title_repeat / structure_repeat）。"""
    issues: list[dict] = []

    # 1. 标题重复：规范化后完全相同且长度 ≥4
    title_groups: dict[str, list[int]] = {}
    for ch in chapters:
        key = _norm(ch.get("title") or "")
        if len(key) >= _TITLE_MIN_CHARS:
            title_groups.setdefault(key, []).append(ch["index"])
    for key, indexes in title_groups.items():
        if len(indexes) >= 2:
            issues.append({
                "type": "title_repeat",
                "chapter_indexes": indexes,
                "detail": (
                    f"章节标题「{key}」重复 {len(indexes)} 次（第{'/'.join(map(str, indexes))}章）。"
                    f"请更换标题，避免同一主题循环。"
                ),
            })

    # 2. 结尾主题词指纹：每章结尾命中 ≥2 个主题词 = 模板结尾；≥3 章 → 结构重复
    template_tails = []
    for ch in chapters:
        tail = _norm((ch.get("content") or "")[-_TAIL_CHARS:])
        hits = [w for w in _TOPIC_WORDS if w in tail]
        if len(hits) >= _TOPIC_HITS_MIN:
            template_tails.append((ch["index"], hits))
    if len(template_tails) >= _CLUSTER_MIN:
        indexes = sorted(i for i, _ in template_tails)
        issues.append({
            "type": "structure_repeat",
            "chapter_indexes": indexes,
            "detail": (
                f"第{'/'.join(map(str, indexes))}章的结尾句式结构高度雷同（命中主题词："
                f"「{'、'.join(template_tails[0][1][:5])}」等，共 {len(template_tails)} 章）。"
                f"疑似模板循环（如「换名城」副本）。建议：更换冲突类型/人物关系/解法，"
                f"或在结局设计上制造差异。"
            ),
        })

    return issues
