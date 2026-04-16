from app.core.token_budget import TokenBudgetManager


class ContextCompressor:
    @classmethod
    def compress_previous_chapters(cls, chapters: list[dict], target_tokens: int) -> str:
        result = []
        current_tokens = 0
        for chapter in reversed(chapters):
            summary = f"第{chapter['index']}章《{chapter['title']}》：{chapter.get('summary', '')}"
            tokens = TokenBudgetManager.estimate_tokens(summary)
            if current_tokens + tokens <= target_tokens:
                result.insert(0, summary)
                current_tokens += tokens
            else:
                break
        return "\n".join(result)
