import re


ASCII_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:[-_'][A-Za-z0-9]+)*")
CJK_CHAR_RE = re.compile(r"[\u4e00-\u9fff]")


def count_words(content: str) -> int:
    text = content or ""
    return len(ASCII_WORD_RE.findall(text)) + len(CJK_CHAR_RE.findall(text))
