"""迭代与令牌预算（hermes-agent 模式：consume/refund，护栏之一）。"""
from __future__ import annotations

from app.agent.providers.base import Usage


class IterationBudget:
    def __init__(self, max_iterations: int) -> None:
        self.max_iterations = max_iterations
        self._used = 0

    def consume(self) -> bool:
        if self._used >= self.max_iterations:
            return False
        self._used += 1
        return True

    def refund(self) -> None:
        if self._used > 0:
            self._used -= 1

    @property
    def remaining(self) -> int:
        return self.max_iterations - self._used

    @property
    def exhausted(self) -> bool:
        return self._used >= self.max_iterations


class TokenBudget:
    def __init__(self, max_tokens: int | None) -> None:
        self.max_tokens = max_tokens
        self.spent = 0

    def add(self, usage: Usage) -> None:
        self.spent += usage.total_tokens

    @property
    def exhausted(self) -> bool:
        return self.max_tokens is not None and self.spent >= self.max_tokens
