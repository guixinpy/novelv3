from app.models import WritingAgentRun, WritingAgentStep
from app.services.writing_agent.agent_stop_hooks import evaluate_agent_stop_hooks


def test_stop_hooks_block_critical_loop_risk():
    run = WritingAgentRun(project_id="project-1", goal="loop", status="running", input={})
    steps = [
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=index,
            tool_name="describe_agent_tools",
            status="success",
            input={"params": {"chapter_index": 1}},
            output={"status": "completed"},
        )
        for index in range(1, 6)
    ]

    decision = evaluate_agent_stop_hooks(run, steps, steps[-1].output)

    assert decision["status"] == "blocked"
    assert decision["reason"] == "loop_risk_critical"
    assert decision["severity"] == "error"
    assert decision["allow_continue"] is False
    assert decision["recommended_tools"] == ["inspect_agent_health_projection", "inspect_agent_trace_audit"]
    assert decision["hooks"][0]["code"] == "critical_loop_risk"
    assert decision["hooks"][0]["detector"] == "generic_repeat"


def test_stop_hooks_block_explicit_budget_cap():
    run = WritingAgentRun(
        project_id="project-1",
        goal="budget",
        status="running",
        input={"agent_loop_budget": {"max_iterations": 2}},
    )
    steps = [
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=1,
            tool_name="describe_agent_tools",
            status="success",
            output={"status": "completed"},
        ),
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=2,
            tool_name="inspect_agent_memory_route",
            status="success",
            output={"status": "completed"},
        ),
    ]

    decision = evaluate_agent_stop_hooks(run, steps, steps[-1].output)

    assert decision["status"] == "blocked"
    assert decision["reason"] == "budget_cap_reached"
    assert decision["severity"] == "error"
    assert decision["allow_continue"] is False
    assert decision["recommended_tools"] == ["inspect_agent_health_projection", "inspect_agent_trace_audit"]
    assert decision["hooks"][0]["code"] == "budget_cap_reached"
    assert decision["hooks"][0]["max_iterations"] == 2
    assert decision["hooks"][0]["used_iterations"] == 2


def test_stop_hooks_block_explicit_max_turns():
    run = WritingAgentRun(
        project_id="project-1",
        goal="turn cap",
        status="running",
        input={"agent_loop_limits": {"max_turns": 2}},
    )
    steps = [
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=1,
            tool_name="describe_agent_tools",
            status="success",
            output={"status": "completed"},
        ),
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=2,
            tool_name="inspect_agent_memory_route",
            status="success",
            output={"status": "completed"},
        ),
    ]

    decision = evaluate_agent_stop_hooks(run, steps, steps[-1].output)

    assert decision["status"] == "blocked"
    assert decision["reason"] == "max_turns_reached"
    assert decision["severity"] == "error"
    assert decision["allow_continue"] is False
    assert decision["recommended_tools"] == ["inspect_agent_health_projection", "inspect_agent_trace_audit"]
    assert decision["hooks"][0]["code"] == "max_turns_reached"
    assert decision["hooks"][0]["max_turns"] == 2
    assert decision["hooks"][0]["used_turns"] == 2


def test_stop_hooks_ignore_implicit_planned_step_count_as_budget_cap():
    run = WritingAgentRun(
        project_id="project-1",
        goal="default budget",
        status="success",
        input={"tools": [{"tool_name": "describe_agent_tools", "params": {}}]},
    )
    steps = [
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=1,
            tool_name="describe_agent_tools",
            status="success",
            output={"status": "completed"},
        )
    ]

    decision = evaluate_agent_stop_hooks(run, steps, steps[-1].output)

    assert decision["status"] == "clear"
    assert decision["reason"] == "no_stop_hook_triggered"
    assert decision["allow_continue"] is True


def test_stop_hooks_block_missing_approval_contract():
    run = WritingAgentRun(project_id="project-1", goal="approval", status="blocked", input={})
    output = {"status": "blocked", "reason": "agent_plan_approval_verification_missing"}
    steps = [
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=1,
            tool_name="execute_longform_chapter_batch",
            status="blocked",
            output=output,
        )
    ]

    decision = evaluate_agent_stop_hooks(run, steps, output)

    assert decision["status"] == "blocked"
    assert decision["reason"] == "approval_required"
    assert decision["severity"] == "error"
    assert decision["allow_continue"] is False
    assert decision["recommended_tools"] == [
        "preview_agent_plan_approval_contract",
        "verify_agent_plan_approval_contract",
    ]
    assert decision["hooks"][0]["code"] == "missing_approval_contract"


def test_stop_hooks_block_memory_provenance_recovery():
    run = WritingAgentRun(project_id="project-1", goal="memory", status="blocked", input={})
    output = {
        "status": "completed",
        "memory_provenance": {
            "status": "blocked",
            "recovery": {
                "status": "recommended",
                "reason": "longform_memory_needs_maintenance",
                "next_tools": ["prepare_repair_longform_maintenance"],
            },
        },
    }
    steps = [
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=1,
            tool_name="summarize_longform_context",
            status="success",
            output=output,
        )
    ]

    decision = evaluate_agent_stop_hooks(run, steps, output)

    assert decision["status"] == "blocked"
    assert decision["reason"] == "memory_provenance_blocked"
    assert decision["allow_continue"] is False
    assert decision["recommended_tools"] == ["prepare_repair_longform_maintenance"]
    assert decision["hooks"][0]["code"] == "memory_provenance_blocked"


def test_stop_hooks_block_context_guard_open():
    run = WritingAgentRun(project_id="project-1", goal="context", status="blocked", input={})
    output = {
        "status": "blocked",
        "risks": [{"code": "context_guard_open", "severity": "error"}],
        "recovery": {
            "status": "recommended",
            "reason": "context_guard_open",
            "next_tools": ["inspect_agent_memory_route"],
        },
    }
    steps = [
        WritingAgentStep(
            project_id="project-1",
            run_id="run-1",
            step_index=1,
            tool_name="inspect_agent_context_compression_projection",
            status="success",
            output=output,
        )
    ]

    decision = evaluate_agent_stop_hooks(run, steps, output)

    assert decision["status"] == "blocked"
    assert decision["reason"] == "context_guard_open"
    assert decision["allow_continue"] is False
    assert decision["recommended_tools"] == ["inspect_agent_memory_route"]
    assert decision["hooks"][0]["code"] == "context_guard_open"
