from types import SimpleNamespace

from app.services.writing_agent.agent_loop_budget import build_agent_loop_budget


def test_loop_budget_refunds_successful_read_tools():
    steps = [
        _step("describe_agent_tools", status="success"),
        _step("generate_chapter", status="success"),
        _step("inspect_agent_health_projection", status="success"),
    ]

    budget = build_agent_loop_budget(steps, max_iterations=3)

    assert budget == {
        "max_iterations": 3,
        "used_iterations": 3,
        "charged_iterations": 1,
        "refunded_iterations": 2,
        "remaining_iterations": 2,
        "refund_policy": {
            "version": "phase227.agent_loop_budget_refund.v1",
            "refundable_mutability": ["read"],
            "refundable_statuses": ["success"],
        },
    }


def test_loop_budget_charges_failed_read_tools_and_unknown_tools():
    steps = [
        _step("describe_agent_tools", status="failed"),
        _step("missing_agent_tool", status="success"),
    ]

    budget = build_agent_loop_budget(steps, max_iterations=2)

    assert budget["used_iterations"] == 2
    assert budget["charged_iterations"] == 2
    assert budget["refunded_iterations"] == 0
    assert budget["remaining_iterations"] == 0


def _step(tool_name: str, *, status: str):
    return SimpleNamespace(tool_name=tool_name, status=status)
