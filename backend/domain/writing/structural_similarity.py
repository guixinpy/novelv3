"""结构级重复检测纯函数（T5 弱化版）。

仅保留对任何题材成立的工程不变量：标题重复检测（防占位符/循环标题）。
结尾主题词指纹已于 2026-08-02 移除（多视角评审：词表是单本书补丁，题材特化会污染创作自由；
「结构重复」本身非普适不变量——单元剧/日常文允许重复结构）。

确定性规则，无 NLP 依赖；只提示不强制。
"""
from __future__ import annotations

import re

_TITLE_MIN_CHARS = 4  # 占位符标题（如「第31章」）不参与
_CLUSTER_MIN = 2      # 标题重复最少章数

_PUNCT_RE = re.compile(r"[-，。！？、；：""''（）·_]+")


def _norm(text: str) -> str:
    return _PUNCT_RE.sub("", text or "")


def detect_structure_repeats(chapters: list[dict]) -> list[dict]:
    """输入 [{index, title, content}]，输出 issues（title_repeat）。

    标题重复：规范化后完全相同且长度 ≥4 的标题出现 ≥2 次。
    """
    issues: list[dict] = []

    title_groups: dict[str, list[int]] = {}
    for ch in chapters:
        key = _norm(ch.get("title") or "")
        if len(key) >= _TITLE_MIN_CHARS:
            title_groups.setdefault(key, []).append(ch["index"])
    for key, indexes in title_groups.items():
        if len(indexes) >= _CLUSTER_MIN:
            issues.append({
                "type": "title_repeat",
                "chapter_indexes": indexes,
                "detail": (
                    f"章节标题「{key}」重复 {len(indexes)} 次（第{'/'.join(map(str, indexes))}章）。"
                    f"请更换标题，避免同一主题循环。"
                ),
            })

    return issues
