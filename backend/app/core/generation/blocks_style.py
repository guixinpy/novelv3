from app.core.model_call_trace import build_context_block
from app.core.prompt_optimizer import PromptOptimizer
from app.models import Project


def build_style_rule_block(project: Project) -> dict | None:
    rules = PromptOptimizer().build_rules(project.style_config)
    if not rules:
        return None

    content = "【用户偏好规则】\n" + "\n".join(f"- {rule}" for rule in rules)
    return build_context_block(
        key="style_rule",
        kind="style_rule",
        title="风格偏好规则",
        content=content,
        sources=[
            {
                "source_type": "Project",
                "source_id": project.id,
                "label": "Project/style_config",
                "source_ref": "Project/style_config",
                "metadata": {"style_config": project.style_config},
            }
        ],
    )
