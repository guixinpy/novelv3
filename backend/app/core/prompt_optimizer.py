class PromptOptimizer:
    RULE_MAP = {
        "description_density": {
            4: "增加环境描写和感官细节",
            5: "大量使用环境描写、感官细节和意象",
            1: "极简描写，只保留关键信息",
            2: "减少环境描写，聚焦动作和对话",
        },
        "dialogue_ratio": {
            1: "减少对话比例，增加叙述和心理描写",
            2: "适当减少对话，增加叙述",
            4: "增加对话比例，用对话推动情节",
            5: "大量使用对话，以对话为主要叙事手段",
        },
        "pacing_speed": {
            1: "慢节奏铺垫，注重氛围营造",
            2: "适当放慢节奏，增加细节",
            4: "加快节奏，减少铺垫",
            5: "快节奏推进，紧凑叙事",
        },
    }

    TONE_MAP = {
        "dark": "保持压抑、沉重的叙事基调",
        "realistic": "写实风格，注重细节真实感",
        "light": "轻松明快的叙事风格",
        "suspense": "悬疑氛围，适当设置悬念",
    }

    def optimize(self, base_prompt: str, config: dict | None) -> str:
        if not config:
            return base_prompt
        rules = self._build_rules(config)
        if rules:
            base_prompt += "\n\n【用户偏好规则】\n" + "\n".join(f"- {r}" for r in rules)
        return base_prompt

    def _build_rules(self, config: dict) -> list[str]:
        rules = []
        for key in ("description_density", "dialogue_ratio", "pacing_speed"):
            val = config.get(key, 3)
            if val != 3 and val in self.RULE_MAP.get(key, {}):
                rules.append(self.RULE_MAP[key][val])
        for tone in config.get("tone_preferences", []):
            if tone in self.TONE_MAP:
                rules.append(self.TONE_MAP[tone])
        return rules
