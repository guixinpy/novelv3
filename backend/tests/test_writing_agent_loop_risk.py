from types import SimpleNamespace

from app.services.writing_agent.agent_loop_risk import build_agent_loop_risk


def test_loop_risk_detects_generic_repeat_with_recovery_action():
    steps = [_step("describe_agent_tools", {"chapter_index": 1}) for _ in range(3)]

    risk = build_agent_loop_risk(steps, known_tool_names={"describe_agent_tools"})

    assert risk["status"] == "warning"
    assert risk["detector"] == "generic_repeat"
    assert risk["tool_name"] == "describe_agent_tools"
    assert risk["max_repeat_count"] == 3
    assert risk["detectors"][0]["detector"] == "generic_repeat"
    assert risk["detectors"][0]["evidence"][0]["tool_name"] == "describe_agent_tools"
    assert risk["recommended_next_action"] == {
        "status": "recommended",
        "reason": "loop_risk_generic_repeat",
        "next_tool": "inspect_agent_health_projection",
        "recommended_tools": ["inspect_agent_health_projection"],
        "requires_user_input": False,
        "allow_continue": True,
    }


def test_loop_risk_detects_ping_pong_pattern():
    steps = [
        _step("review_chapter_quality", {"chapter_index": 1}),
        _step("plan_chapter_revision", {"chapter_index": 1}),
        _step("review_chapter_quality", {"chapter_index": 1}),
        _step("plan_chapter_revision", {"chapter_index": 1}),
    ]

    risk = build_agent_loop_risk(
        steps,
        known_tool_names={"review_chapter_quality", "plan_chapter_revision"},
    )

    assert risk["status"] == "warning"
    assert risk["detector"] == "ping_pong"
    ping_pong = next(item for item in risk["detectors"] if item["detector"] == "ping_pong")
    assert ping_pong["pattern"] == ["review_chapter_quality", "plan_chapter_revision"]
    assert ping_pong["repeat_count"] == 2
    assert ping_pong["recommended_next_action"]["reason"] == "loop_risk_ping_pong"


def test_loop_risk_detects_known_poll_no_progress():
    steps = [
        _step("inspect_agent_job_projection", {"task_id": "task-1"}, output={"status": "running"})
        for _ in range(3)
    ]

    risk = build_agent_loop_risk(steps, known_tool_names={"inspect_agent_job_projection"})

    assert risk["status"] == "warning"
    assert risk["detector"] == "known_poll_no_progress"
    poll = next(item for item in risk["detectors"] if item["detector"] == "known_poll_no_progress")
    assert poll["tool_name"] == "inspect_agent_job_projection"
    assert poll["repeat_count"] == 3
    assert poll["output_signature"]


def test_loop_risk_detects_unknown_tool_repeat_from_planned_tools():
    planned_tools = [{"tool_name": "missing_agent_tool", "params": {"chapter_index": 1}} for _ in range(5)]
    steps = [
        _step(
            "missing_agent_tool",
            {"chapter_index": 1},
            status="failed",
            error="Unsupported writing agent tool: missing_agent_tool",
        )
    ]

    risk = build_agent_loop_risk(steps, planned_tools=planned_tools, known_tool_names={"describe_agent_tools"})

    assert risk["status"] == "critical"
    assert risk["detector"] == "unknown_tool_repeat"
    unknown = next(item for item in risk["detectors"] if item["detector"] == "unknown_tool_repeat")
    assert unknown["tool_name"] == "missing_agent_tool"
    assert unknown["repeat_count"] == 5
    assert unknown["recommended_next_action"] == {
        "status": "blocked",
        "reason": "loop_risk_unknown_tool_repeat",
        "next_tool": "inspect_agent_health_projection",
        "recommended_tools": ["inspect_agent_health_projection", "describe_agent_tools"],
        "requires_user_input": False,
        "allow_continue": False,
    }


def test_loop_risk_detects_global_circuit_breaker():
    steps = [_step("describe_agent_tools", {"chapter_index": index}) for index in range(1, 31)]

    risk = build_agent_loop_risk(steps, known_tool_names={"describe_agent_tools"})

    assert risk["status"] == "critical"
    assert risk["detector"] == "global_circuit_breaker"
    breaker = next(item for item in risk["detectors"] if item["detector"] == "global_circuit_breaker")
    assert breaker["call_count"] == 30
    assert breaker["thresholds"] == {"critical": 30}
    assert breaker["recommended_next_action"]["allow_continue"] is False


def _step(tool_name, params=None, *, status="success", output=None, error=None):
    return SimpleNamespace(
        tool_name=tool_name,
        status=status,
        input={"params": params or {}},
        output=output or {"status": "completed"},
        error=error,
        step_index=1,
        target_type="agent_tool_plan",
        chapter_index=(params or {}).get("chapter_index"),
        tool_call_id=None,
    )
