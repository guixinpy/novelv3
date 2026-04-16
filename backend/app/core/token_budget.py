import math


class TokenBudgetManager:
    DEFAULT_BUDGET = {
        "total": 6000,
        "system_prompt": 800,
        "characters": 1000,
        "previous_chapters": 1200,
        "world_facts": 800,
        "output_format": 400,
        "reserved": 1200,
    }

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        try:
            import tiktoken
            enc = tiktoken.encoding_for_model("gpt-4")
            return len(enc.encode(text))
        except Exception:
            chinese_chars = len([c for c in text if "\u4e00" <= c <= "\u9fa5"])
            return math.ceil(chinese_chars * 0.6 + len(text.split()) * 0.5)
