from pathlib import Path

from app.prompting.renderer import PromptRenderer, default_prompts_dir


class PromptManager:
    """Legacy compatibility wrapper over PromptRenderer.

    Production prompt assembly must use app.prompting.PromptAssembler with
    prompt IDs registered in app.prompting.registry. Keep this wrapper only for
    compatibility with old tests or utility code that renders a template by
    name.
    """

    def __init__(self, prompts_dir: str | Path | None = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir is not None else default_prompts_dir()
        self.renderer = PromptRenderer(self.prompts_dir)

    def load(self, name: str, variables: dict | None = None) -> str:
        return self.renderer.render(name, variables).content
