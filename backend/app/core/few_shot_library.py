class FewShotExampleLibrary:
    HARDCODED_EXAMPLES: dict[str, dict[str, list[dict]]] = {
        "apocalypse": {
            "chapter": [
                {
                    "input": "末世背景，主角在废墟中醒来",
                    "output": "灰色的天空低垂着，像一块被揉皱的旧布。林森睁开眼，入目的是一片断壁残垣...",
                },
            ],
        },
        "xianxia": {
            "chapter": [
                {
                    "input": "修仙背景，主角初入宗门",
                    "output": "青云山巅，云雾缭绕。少年抬头望去，那座传说中的青云宗大门就在眼前...",
                },
            ],
        },
        "romance": {
            "chapter": [
                {
                    "input": "都市言情，男女主角初次相遇",
                    "output": "咖啡洒在了白衬衫上，她慌忙道歉，抬头却对上了一双深邃的眼睛...",
                },
            ],
        },
    }

    def select_examples(self, task_type: str, genre: str, limit: int = 2) -> list[dict]:
        genre_key = self._match_genre(genre)
        examples = self.HARDCODED_EXAMPLES.get(genre_key, {}).get(task_type, [])
        return examples[:limit]

    def _match_genre(self, genre: str) -> str:
        genre_lower = genre.lower()
        if any(k in genre_lower for k in ("末世", "废土", "apocalypse")):
            return "apocalypse"
        if any(k in genre_lower for k in ("修仙", "仙侠", "xianxia")):
            return "xianxia"
        if any(k in genre_lower for k in ("言情", "恋爱", "romance")):
            return "romance"
        return ""

    def format_for_prompt(self, examples: list[dict]) -> str:
        if not examples:
            return ""
        lines = ["【参考示例】"]
        for i, ex in enumerate(examples, 1):
            lines.append(f"示例 {i}:")
            lines.append(f"输入: {ex['input']}")
            lines.append(f"输出: {ex['output']}")
        return "\n".join(lines)
