import hashlib
from pathlib import Path
from string import Template

from app.prompting.contracts import RenderedTemplate


def default_prompts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts"


class PromptRenderer:
    def __init__(self, prompts_dir: str | Path | None = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir is not None else default_prompts_dir()

    def template_path(self, template_name: str) -> Path:
        self._validate_template_name(template_name)
        return self.prompts_dir / f"{template_name}.txt"

    def render(self, template_name: str, variables: dict | None = None) -> RenderedTemplate:
        path = self.template_path(template_name)
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")

        content = path.read_text(encoding="utf-8")
        if variables:
            try:
                content = Template(content).substitute(variables)
            except KeyError as exc:
                raise KeyError(f"Missing prompt variable '{exc.args[0]}'") from exc

        return RenderedTemplate(
            template_name=template_name,
            content=content,
            template_hash=self.template_hash(template_name),
        )

    def template_hash(self, template_name: str) -> str:
        path = self.template_path(template_name)
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        return f"sha256:{digest}"

    def _validate_template_name(self, template_name: str) -> None:
        if "/" in template_name or "\\" in template_name or ".." in template_name:
            raise ValueError(f"Invalid prompt template name: {template_name}")
