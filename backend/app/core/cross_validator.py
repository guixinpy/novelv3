class CrossValidator:
    def validate(self, l1_facts: list[dict], l2_facts: list[dict]) -> dict:
        confirmed = []
        conflicts = []
        pending = []

        for l2 in l2_facts:
            matched = self._find_match(l2, l1_facts)
            if matched and self._is_consistent(l2, matched):
                l2["validation"] = {"l1_extracted": True, "l2_extracted": True, "cross_confidence": max(l2.get("confidence", 0.5), 0.8)}
                confirmed.append(l2)
            elif matched and not self._is_consistent(l2, matched):
                conflicts.append({"l1": matched, "l2": l2, "reason": "L1/L2 结果不一致"})
            else:
                l2["validation"] = {"l1_extracted": False, "l2_extracted": True, "cross_confidence": l2.get("confidence", 0.5) * 0.7}
                pending.append(l2)

        return {"confirmed": confirmed, "conflicts": conflicts, "pending": pending}

    def _find_match(self, l2_fact: dict, l1_facts: list[dict]) -> dict | None:
        for l1 in l1_facts:
            if l1.get("subject") == l2_fact.get("subject") and l1.get("type") == l2_fact.get("type"):
                return l1
        return None

    def _is_consistent(self, l2: dict, l1: dict) -> bool:
        if l2.get("type") == "character_presence" and l1.get("type") == "character_presence":
            return True
        return l2.get("new_value") == l1.get("new_value") if "new_value" in l2 and "new_value" in l1 else True
