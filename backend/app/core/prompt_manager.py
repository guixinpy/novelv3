import os
from string import Template


class PromptManager:
    def __init__(self, prompts_dir: str | None = None):
        if prompts_dir is None:
            self.prompts_dir = os.path.join(
                os.path.dirname(__file__), "..", "..", "prompts"
            )
        else:
            self.prompts_dir = prompts_dir

    def load(self, name: str, variables: dict | None = None) -> str:
        path = os.path.join(self.prompts_dir, f"{name}.txt")
        if not os.path.exists(path):
            raise FileNotFoundError(f"Prompt not found: {path}")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if variables:
            content = Template(content).substitute(variables)
        return content
