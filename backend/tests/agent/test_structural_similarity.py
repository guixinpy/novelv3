"""结构级重复检测纯函数测试（T5 弱化版：仅标题重复）。"""
from __future__ import annotations

from domain.writing.structural_similarity import detect_structure_repeats


def _ch(index: int, title: str, content: str) -> dict:
    return {"index": index, "title": title, "content": content}


def test_title_repeat_detected():
    # 200 章实证：「渡到底的是心」出现 3 次（ch38/65/80）
    chapters = [
        _ch(38, "渡到底的是心", "正文一。" * 50),
        _ch(65, "渡到底的是心", "正文二。" * 50),
        _ch(80, "渡到底的是心", "正文三。" * 50),
    ]
    issues = detect_structure_repeats(chapters)
    title_issue = next(i for i in issues if i["type"] == "title_repeat")
    assert title_issue["chapter_indexes"] == [38, 65, 80]
    assert "渡到底的是心" in title_issue["detail"]


def test_title_repeat_short_title_not_reported():
    # 占位符标题（如「第31章」）太短不报
    chapters = [
        _ch(1, "第1章", "正文。" * 50),
        _ch(2, "第2章", "正文。" * 50),
        _ch(3, "第3章", "正文。" * 50),
    ]
    issues = detect_structure_repeats(chapters)
    assert not any(i["type"] == "title_repeat" for i in issues)


def test_clean_chapters_no_issues():
    chapters = [
        _ch(1, "面馆接头", "雾城的夜里，面馆的灯亮着。" * 20 + "电话铃响了。"),
        _ch(2, "仓库对峙", "仓库里堆满旧铁柜。" * 20 + "脚步声从雾里传来。"),
        _ch(3, "码头旧账", "码头的水声拍打石阶。" * 20 + "有人把账本推了过来。"),
    ]
    assert detect_structure_repeats(chapters) == []
