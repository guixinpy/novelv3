from app.core.text_stats import count_words


def test_count_words_counts_chinese_chars_without_extra_segment():
    assert count_words("新正文。星环钥匙第二形态启动。") == 13


def test_count_words_counts_ascii_words_and_cjk_chars_without_double_counting():
    assert count_words("alpha beta 第一章") == 5
