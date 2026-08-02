"""JSON 解析公共纯函数（v1 绞杀：从 deepseek_adapter/prompting 迁出）。"""
from __future__ import annotations

import json
import re

_UNICODE_ESCAPE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


def parse_json_safely(text: str) -> dict:
    """健壮 JSON 解析：直接解析 → ```json 代码块 → 首个 {..}/[..] 片段。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        candidate = match.group(1).replace("'", '"')
        candidate = re.sub(r",(\s*[}\]])", r"\1", candidate)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    raise ValueError(f"无法解析为 JSON：{text[:200]}")


def normalise_json_text(value: str) -> str:
    """规范化 JSON 文本：有效 JSON 重新序列化；否则解码 \\u 转义。"""
    try:
        return json.dumps(json.loads(value), ensure_ascii=False)
    except ValueError:
        return _UNICODE_ESCAPE_RE.sub(lambda match: chr(int(match.group(1), 16)), value)
