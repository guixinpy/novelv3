"""提示词渲染与 trace 元数据（生成统一 v2：原 renderer/tracing/registry 的内联版）。

模板文件在 backend/prompts/*.txt，string.Template（${var}）渲染，与旧 renderer 语义一致。
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from string import Template
from typing import Any

_PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"


def render_prompt(template_name: str, variables: dict | None = None) -> str:
    """读 backend/prompts/{template_name}.txt 并渲染。缺失变量抛 KeyError（与旧语义一致）。"""
    path = _PROMPTS_DIR / f"{template_name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    try:
        return Template(path.read_text(encoding="utf-8")).substitute(variables or {})
    except KeyError as exc:
        raise KeyError(f"Missing prompt variable '{exc.args[0]}'") from exc


def template_hash(template_name: str) -> str:
    path = _PROMPTS_DIR / f"{template_name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def prompt_trace_metadata(
    *,
    prompt_id: str,
    template_name: str,
    budget_report: dict[str, Any] | None = None,
    version: str = "1",
) -> dict[str, Any]:
    """trace_metadata 结构（与旧 build_prompt_trace_metadata 一致）。"""
    return {
        "prompt_id": prompt_id,
        "prompt_version": version,
        "template_name": template_name,
        "template_hash": template_hash(template_name),
        "budget": budget_report,
    }
