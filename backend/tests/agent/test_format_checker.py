"""输出格式校验纯函数测试（T4，样本取自 200 章评审实证）。"""
from __future__ import annotations

from domain.writing.format_checker import check_chapter_hook, check_text_format


def _types(issues: list[dict]) -> list[str]:
    return [i["type"] for i in issues]


# ── R1: 五类格式检查 ──


def test_markdown_bold_residue():
    # 评审实证：ch105「同**道理**一般」
    issues = check_text_format("他沉默片刻。\n同**道理**一般。")
    assert "markdown_bold" in _types(issues)


def test_slash_alternative_words():
    # 评审实证：ch105「刮去/凿掉/磨平了」——模型把备选词写进正文
    issues = check_text_format("有人把名字刮去/凿掉/磨平了。")
    assert "slash_alternative" in _types(issues)


def test_chapter_title_line_in_body():
    # 评审实证：ch101-201 每章正文开头自带「第101章　漂来的小船」
    issues = check_text_format("第101章　漂来的小船\n\n小船漂到岸边。")
    assert "chapter_title_line" in _types(issues)


def test_unbalanced_full_width_quotes():
    # 只有开引号没有闭引号
    issues = check_text_format("她说：“明天就走。\n他点点头。")
    assert "unbalanced_quotes" in _types(issues)


def test_half_width_punctuation_mixed():
    # 评审实证：ch2「睡不着,」、ch100「你今日不去局里了?」
    issues = check_text_format("他睡不着,又坐起来。")
    assert "half_width_punct" in _types(issues)


def test_clean_text_passes():
    text = "他睡不着，又坐起来。\n“明天就走。”她说。\n他点了点头。"
    assert check_text_format(text) == []


# ── R2: 每章卡点校验 ──


def test_hook_missing_at_end():
    # 评审实证：ch195 类「继续往前走去」式无钩子结尾
    issues = check_chapter_hook("雾越来越重。他继续往前走去。")
    assert "weak_hook" in _types(issues)


def test_hook_missing_guarding_style():
    # 评审实证：ch180「他极静极稳地立着」式结尾
    issues = check_chapter_hook("水光晃动。他极静极稳地立着。")
    assert "weak_hook" in _types(issues)


def test_hook_with_dialogue_not_reported():
    issues = check_chapter_hook("“跟我来。”他伸手抓住她的手腕，朝码头走去。")
    assert issues == []


def test_hook_with_action_not_reported():
    issues = check_chapter_hook("他摸到口袋里那枚符记，指尖微微发烫。")
    assert issues == []
