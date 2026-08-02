from app.agent.budget import IterationBudget, TokenBudget
from app.agent.providers.base import Usage


def test_iteration_budget_consume_and_exhaust():
    budget = IterationBudget(max_iterations=2)
    assert budget.consume() is True
    assert budget.consume() is True
    assert budget.consume() is False
    assert budget.exhausted


def test_iteration_budget_refund():
    budget = IterationBudget(max_iterations=1)
    assert budget.consume() is True
    budget.refund()
    assert budget.consume() is True
    assert budget.consume() is False


def test_iteration_budget_remaining():
    budget = IterationBudget(max_iterations=3)
    budget.consume()
    assert budget.remaining == 2


def test_token_budget_accumulates_usage():
    budget = TokenBudget(max_tokens=100)
    budget.add(Usage(prompt_tokens=30, completion_tokens=20))
    assert budget.spent == 50
    assert not budget.exhausted
    budget.add(Usage(prompt_tokens=40, completion_tokens=20))
    assert budget.spent == 110
    assert budget.exhausted


def test_token_budget_unlimited_when_none():
    budget = TokenBudget(max_tokens=None)
    budget.add(Usage(prompt_tokens=10**9, completion_tokens=0))
    assert not budget.exhausted
