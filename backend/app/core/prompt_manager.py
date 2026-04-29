from pathlib import Path

from app.prompting.renderer import PromptRenderer, default_prompts_dir


class PromptManager:
    def __init__(self, prompts_dir: str | Path | None = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir is not None else default_prompts_dir()
        self.renderer = PromptRenderer(self.prompts_dir)

    def load(self, name: str, variables: dict | None = None) -> str:
        return self.renderer.render(name, variables).content
