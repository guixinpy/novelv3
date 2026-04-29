from dataclasses import asdict
from typing import Any

from app.prompting.contracts import PromptBuildResult


def build_prompt_trace_metadata(build_result: PromptBuildResult) -> dict[str, Any]:
    budget = asdict(build_result.budget_report) if build_result.budget_report else None
    return {
        "prompt_id": build_result.prompt_id,
        "prompt_version": build_result.version,
        "template_name": build_result.template_name,
        "template_hash": build_result.template_hash,
        "budget": budget,
    }
