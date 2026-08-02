"""输出格式校验纯函数（T4 格式守门员）。

确定性规则，供 check_chapter_format 工具调用；只报明确模式，不误伤正常文本。
样本取自 200 章评审实证：`**` 渗入正文、`/` 备选词残留、正文自带章题行、
全角引号归零、半角标点混用、无钩子收尾。
"""
from __future__ import annotations

import re

# 1. markdown 加粗残留（ch105「同**道理**一般」）
_MARKDOWN_BOLD = re.compile(r"\*\*")
# 2. 备选词残留：中文语境 X/Y（ch105「刮去/凿掉/磨平了」）；URL/数字比例不受影响
_SLASH_ALT = re.compile(r"[一-鿿]{1,6}/[一-鿿]{1,6}")
# 3. 正文自带章题行（ch101-201 每章开头「第101章　漂来的小船」）
_CHAPTER_TITLE_LINE = re.compile(r"^第\s*\d+\s*章[\s　]+\S+", re.MULTILINE)
# 5. 半角标点混用：中文相邻的半角 ,.;:?!（ch2「睡不着,」、ch100「你今日不去局里了?」）
_HALF_PUNCT = re.compile(r"[一-鿿][,.;:?!]|[,.;:?!][一-鿿]")

# 卡点：无钩子收尾句式（200 章实证：ch160-201 几乎每章以此类结尾）
_WEAK_HOOK_PATTERNS = (
    "继续往前走去",
    "继续往前",
    "望着那道光",
    "极静极稳地立",
    "极缓极缓",
    "守着这",
    "心里的那句",
)


def check_text_format(text: str) -> list[dict]:
    """五类格式检查，返回 issues 列表（空 = 通过）。"""
    issues: list[dict] = []

    if _MARKDOWN_BOLD.search(text):
        issues.append({
            "severity": "error",
            "type": "markdown_bold",
            "detail": "正文含 markdown 加粗标记 **，属于格式污染，应去除。",
        })

    for m in _SLASH_ALT.finditer(text):
        issues.append({
            "severity": "error",
            "type": "slash_alternative",
            "detail": f"正文含备选词残留「{m.group()}」，模型只应保留一个选项。",
        })
        break

    for m in _CHAPTER_TITLE_LINE.finditer(text):
        issues.append({
            "severity": "error",
            "type": "chapter_title_line",
            "detail": f"正文开头自带章题行「{m.group()[:20]}」，与章节标题重复，应删除。",
        })
        break

    open_q = text.count("“")
    close_q = text.count("”")
    if open_q != close_q:
        issues.append({
            "severity": "warning",
            "type": "unbalanced_quotes",
            "detail": f"全角引号不成对：开引号 {open_q} 个、闭引号 {close_q} 个。请检查对话标点。",
        })

    for m in _HALF_PUNCT.finditer(text):
        issues.append({
            "severity": "warning",
            "type": "half_width_punct",
            "detail": f"中文语境使用半角标点「{m.group()}」，应改用全角。",
        })
        break

    return issues


def check_chapter_hook(text: str) -> list[dict]:
    """章末卡点：结尾 100 字符内无对话且命中无钩子句式 → 提示重写结尾。"""
    tail = text[-100:]
    if "“" in tail or "”" in tail or '"' in tail:
        return []  # 结尾有对话 = 存在交互，不算无钩子
    for pattern in _WEAK_HOOK_PATTERNS:
        if pattern in tail:
            return [{
                "severity": "warning",
                "type": "weak_hook",
                "detail": (
                    f"本章结尾「…{pattern}…」式收尾可能缺乏悬念/信息增量，读者没有翻页理由。"
                    f"建议在章末留下未解决的张力点（新线索/冲突升级/悬念）。"
                ),
            }]
    return []
