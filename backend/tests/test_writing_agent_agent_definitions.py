from app.services.writing_agent.agent_definitions import (
    AGENT_DEFINITION_VERSION,
    AGENT_DEFINITION_REGISTRY_AUDIT_VERSION,
    inspect_agent_definition_registry,
    load_agent_definition,
)
from app.services.writing_agent.agent_worker_dispatch import (
    AGENT_WORKER_DISPATCH_VERSION,
    AGENT_WORKER_ROUTE_REGISTRY_AUDIT_VERSION,
    inspect_agent_worker_route_registry,
    preview_agent_worker_dispatch,
    preview_agent_worker_dispatches,
)


def test_reviewer_agent_definition_loads_from_repo_yaml():
    definition = load_agent_definition("reviewer")

    assert definition["version"] == AGENT_DEFINITION_VERSION
    assert definition["status"] == "ready"
    assert definition["name"] == "reviewer"
    assert definition["role"] == "worker"
    assert definition["max_depth"] == 0
    assert definition["can_dispatch_children"] is False
    assert definition["allowed_tools"] == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "inspect_agent_world_model_route",
    ]
    assert definition["write_policy"] == {
        "mode": "read_only_review",
        "allow_writes": False,
        "guarded_writes": "deny",
        "child_dispatch": "deny",
    }


def test_worker_dispatch_preview_returns_non_executing_task_envelopes():
    preview = preview_agent_worker_dispatch(
        "reviewer",
        [
            {"tool_name": "review_chapter_quality", "params": {"chapter_index": 3}},
            {"tool_name": "inspect_agent_world_model_route", "params": {"chapter_index": 3}},
        ],
        parent_run_id="run-review-1",
    )

    assert preview["version"] == AGENT_WORKER_DISPATCH_VERSION
    assert preview["status"] == "ready"
    assert preview["worker"]["name"] == "reviewer"
    assert preview["worker"]["can_dispatch_children"] is False
    assert preview["summary"] == {"planned_tasks": 2, "blocked_tasks": 0, "issues": 0}
    assert preview["task_envelopes"] == [
        {
            "status": "planned",
            "worker": "reviewer",
            "role": "worker",
            "tool_name": "review_chapter_quality",
            "params": {"chapter_index": 3},
            "parent_run_id": "run-review-1",
            "dispatch_mode": "preview_only",
            "will_execute": False,
            "child_dispatch_allowed": False,
        },
        {
            "status": "planned",
            "worker": "reviewer",
            "role": "worker",
            "tool_name": "inspect_agent_world_model_route",
            "params": {"chapter_index": 3},
            "parent_run_id": "run-review-1",
            "dispatch_mode": "preview_only",
            "will_execute": False,
            "child_dispatch_allowed": False,
        },
    ]
    assert preview["issues"] == []


def test_worker_dispatch_preview_blocks_child_dispatch_and_disallowed_tools():
    preview = preview_agent_worker_dispatch(
        "reviewer",
        [
            {
                "tool_name": "review_chapter_quality",
                "params": {"chapter_index": 3},
                "children": [{"tool_name": "generate_chapter"}],
            },
            {"tool_name": "generate_chapter", "params": {"chapter_index": 4}},
        ],
        parent_run_id="run-review-blocked",
    )

    assert preview["status"] == "blocked"
    assert preview["summary"] == {"planned_tasks": 0, "blocked_tasks": 2, "issues": 2}
    assert preview["task_envelopes"][0]["status"] == "blocked"
    assert preview["task_envelopes"][0]["issue_codes"] == ["child_dispatch_not_allowed"]
    assert preview["task_envelopes"][1]["status"] == "blocked"
    assert preview["task_envelopes"][1]["issue_codes"] == ["tool_not_allowed_for_worker"]
    assert preview["issues"] == [
        {
            "code": "child_dispatch_not_allowed",
            "severity": "error",
            "tool_name": "review_chapter_quality",
            "worker": "reviewer",
        },
        {
            "code": "tool_not_allowed_for_worker",
            "severity": "error",
            "tool_name": "generate_chapter",
            "worker": "reviewer",
        },
    ]


def test_worker_dispatch_routes_memory_activation_to_memory_worker():
    preview = preview_agent_worker_dispatches(
        [
            {
                "tool_name": "inspect_agent_memory_activation_plan",
                "params": {"chapter_index": 3},
            }
        ],
        parent_run_id="run-memory-activation",
    )

    assert preview["status"] == "ready"
    assert preview["summary"] == {"workers": 1, "planned_tasks": 1, "blocked_tasks": 0, "issues": 0}
    dispatch = preview["worker_dispatches"][0]
    assert dispatch["worker"]["name"] == "memory_worker"
    assert dispatch["task_envelopes"][0]["tool_name"] == "inspect_agent_memory_activation_plan"


def test_worker_dispatch_routes_context_compression_to_memory_worker():
    preview = preview_agent_worker_dispatches(
        [
            {
                "tool_name": "inspect_agent_context_compression_projection",
                "params": {"chapter_index": 8},
            },
            {
                "tool_name": "build_agent_context_compression_payload",
                "params": {"chapter_index": 8},
            },
            {
                "tool_name": "record_agent_context_compression_summary",
                "params": {"chapter_index": 8},
            },
        ],
        parent_run_id="run-context-compression",
    )

    assert preview["status"] == "ready"
    assert preview["summary"] == {"workers": 1, "planned_tasks": 3, "blocked_tasks": 0, "issues": 0}
    dispatch = preview["worker_dispatches"][0]
    assert dispatch["worker"]["name"] == "memory_worker"
    assert [item["tool_name"] for item in dispatch["task_envelopes"]] == [
        "inspect_agent_context_compression_projection",
        "build_agent_context_compression_payload",
        "record_agent_context_compression_summary",
    ]


def test_worker_dispatch_routes_preflight_to_drafting_worker():
    preview = preview_agent_worker_dispatches(
        [
            {
                "tool_name": "preflight_writing",
                "params": {"chapter_index": 8},
            }
        ],
        parent_run_id="run-preflight-worker",
    )

    assert preview["status"] == "ready"
    assert preview["summary"] == {"workers": 1, "planned_tasks": 1, "blocked_tasks": 0, "issues": 0}
    dispatch = preview["worker_dispatches"][0]
    assert dispatch["worker"]["name"] == "drafting_worker"
    assert dispatch["task_envelopes"][0]["tool_name"] == "preflight_writing"


def test_worker_dispatch_routes_story_asset_approval_wrappers_to_drafting_worker():
    tool_names = [
        "prepare_generate_setup_execution",
        "execute_generate_setup_with_approval",
        "prepare_generate_storyline_execution",
        "execute_generate_storyline_with_approval",
        "prepare_generate_outline_execution",
        "execute_generate_outline_with_approval",
    ]
    preview = preview_agent_worker_dispatches(
        [{"tool_name": tool_name, "params": {"command_args": "雾港悬疑"}} for tool_name in tool_names],
        parent_run_id="run-story-assets-approval",
    )

    assert preview["status"] == "ready"
    assert preview["summary"] == {"workers": 1, "planned_tasks": 6, "blocked_tasks": 0, "issues": 0}
    dispatch = preview["worker_dispatches"][0]
    assert dispatch["worker"]["name"] == "drafting_worker"
    assert [item["tool_name"] for item in dispatch["task_envelopes"]] == tool_names


def test_worker_dispatch_routes_story_asset_previews_to_drafting_worker():
    tool_names = [
        "preview_generate_setup_execution",
        "preview_generate_storyline_execution",
        "preview_generate_outline_execution",
    ]
    preview = preview_agent_worker_dispatches(
        [{"tool_name": tool_name, "params": {"command_args": "雾港悬疑"}} for tool_name in tool_names],
        parent_run_id="run-story-assets-preview",
    )

    assert preview["status"] == "ready"
    assert preview["summary"] == {"workers": 1, "planned_tasks": 3, "blocked_tasks": 0, "issues": 0}
    dispatch = preview["worker_dispatches"][0]
    assert dispatch["worker"]["name"] == "drafting_worker"
    assert [item["tool_name"] for item in dispatch["task_envelopes"]] == tool_names


def test_worker_dispatch_routes_memory_tree_to_memory_worker():
    preview = preview_agent_worker_dispatches(
        [
            {
                "tool_name": "inspect_agent_memory_tree",
                "params": {"level": "scene", "chapter_index": 8},
            }
        ],
        parent_run_id="run-memory-tree",
    )

    assert preview["status"] == "ready"
    assert preview["summary"] == {"workers": 1, "planned_tasks": 1, "blocked_tasks": 0, "issues": 0}
    dispatch = preview["worker_dispatches"][0]
    assert dispatch["worker"]["name"] == "memory_worker"
    assert dispatch["task_envelopes"][0]["tool_name"] == "inspect_agent_memory_tree"


def test_worker_dispatch_routes_memory_tree_summary_materialization_to_memory_worker():
    preview = preview_agent_worker_dispatches(
        [
            {
                "tool_name": "record_agent_memory_tree_summaries",
                "params": {"chapter_index": 2},
            }
        ],
        parent_run_id="run-memory-tree-summary",
    )

    assert preview["status"] == "ready"
    assert preview["summary"] == {"workers": 1, "planned_tasks": 1, "blocked_tasks": 0, "issues": 0}
    dispatch = preview["worker_dispatches"][0]
    assert dispatch["worker"]["name"] == "memory_worker"
    assert dispatch["task_envelopes"][0]["tool_name"] == "record_agent_memory_tree_summaries"


def test_worker_dispatch_routes_observability_and_dogfood_evidence_to_recovery_worker():
    preview = preview_agent_worker_dispatches(
        [
            {
                "tool_name": "inspect_agent_trace_audit",
                "params": {"run_id": "run-trace"},
            },
            {
                "tool_name": "inspect_agent_job_projection",
                "params": {"chapter_index": 8},
            },
            {
                "tool_name": "inspect_agent_dogfood_evidence",
                "params": {},
            },
            {
                "tool_name": "apply_agent_worker_orphan_recovery",
                "params": {"confirm_apply": True},
            },
        ],
        parent_run_id="run-recovery-observability",
    )

    assert preview["status"] == "ready"
    assert preview["summary"] == {"workers": 1, "planned_tasks": 4, "blocked_tasks": 0, "issues": 0}
    dispatch = preview["worker_dispatches"][0]
    assert dispatch["worker"]["name"] == "recovery_worker"
    assert [item["tool_name"] for item in dispatch["task_envelopes"]] == [
        "inspect_agent_trace_audit",
        "inspect_agent_job_projection",
        "inspect_agent_dogfood_evidence",
        "apply_agent_worker_orphan_recovery",
    ]


def test_agent_definition_registry_audit_binds_worker_profiles_to_yaml_leaf_definitions():
    audit = inspect_agent_definition_registry()

    assert audit["version"] == AGENT_DEFINITION_REGISTRY_AUDIT_VERSION
    assert audit["status"] == "passed"
    assert audit["summary"] == {
        "worker_profiles": 7,
        "ready_worker_definitions": 7,
        "leaf_worker_definitions": 7,
        "issues": 0,
    }
    assert audit["worker_profiles"] == [
        "drafting_worker",
        "memory_worker",
        "recovery_worker",
        "retrieval_worker",
        "reviewer_worker",
        "revision_worker",
        "world_model_worker",
    ]
    assert audit["issues"] == []
    assert {row["profile"] for row in audit["definitions"]} == set(audit["worker_profiles"])
    assert all(row["status"] == "ready" for row in audit["definitions"])
    assert all(row["can_dispatch_children"] is False for row in audit["definitions"])


def test_worker_route_registry_audit_binds_routes_to_allowed_worker_definitions():
    audit = inspect_agent_worker_route_registry()

    assert audit["version"] == AGENT_WORKER_ROUTE_REGISTRY_AUDIT_VERSION
    assert audit["status"] == "passed"
    assert audit["summary"] == {"routes": 51, "ready_routes": 51, "unrouted_allowed_tools": 0, "issues": 0}
    assert audit["issues"] == []
    assert audit["unrouted_allowed_tools"] == []

    routes_by_tool = {route["tool_name"]: route for route in audit["routes"]}
    assert routes_by_tool["preflight_writing"]["worker"] == "drafting_worker"
    assert routes_by_tool["preview_generate_setup_execution"]["worker"] == "drafting_worker"
    assert routes_by_tool["prepare_generate_setup_execution"]["worker"] == "drafting_worker"
    assert routes_by_tool["execute_generate_setup_with_approval"]["worker"] == "drafting_worker"
    assert routes_by_tool["preview_generate_storyline_execution"]["worker"] == "drafting_worker"
    assert routes_by_tool["prepare_generate_storyline_execution"]["worker"] == "drafting_worker"
    assert routes_by_tool["execute_generate_storyline_with_approval"]["worker"] == "drafting_worker"
    assert routes_by_tool["preview_generate_outline_execution"]["worker"] == "drafting_worker"
    assert routes_by_tool["prepare_generate_outline_execution"]["worker"] == "drafting_worker"
    assert routes_by_tool["execute_generate_outline_with_approval"]["worker"] == "drafting_worker"
    assert routes_by_tool["inspect_agent_trace_audit"]["worker"] == "recovery_worker"
    assert routes_by_tool["inspect_agent_job_projection"]["worker"] == "recovery_worker"
    assert routes_by_tool["inspect_agent_dogfood_evidence"]["worker"] == "recovery_worker"
    assert routes_by_tool["apply_agent_worker_orphan_recovery"]["worker"] == "recovery_worker"
    assert routes_by_tool["inspect_agent_memory_activation_plan"]["worker"] == "memory_worker"
    assert routes_by_tool["inspect_agent_context_compression_projection"]["worker"] == "memory_worker"
    assert routes_by_tool["build_agent_context_compression_payload"]["worker"] == "memory_worker"
    assert routes_by_tool["record_agent_context_compression_summary"]["worker"] == "memory_worker"
    assert routes_by_tool["inspect_agent_memory_tree"]["worker"] == "memory_worker"
    assert routes_by_tool["record_agent_memory_tree_summaries"]["worker"] == "memory_worker"
    assert [route["tool_name"] for route in audit["routes"]] == sorted(routes_by_tool)
    assert all(route["definition_status"] == "ready" for route in audit["routes"])
    assert all(route["tool_allowed"] is True for route in audit["routes"])
    assert all(route["can_dispatch_children"] is False for route in audit["routes"])
