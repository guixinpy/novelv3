from __future__ import annotations

from app.services.writing_agent.approval_tool_metadata import build_approval_tool_metadata_by_name


def test_approval_tool_metadata_projects_confirmed_write_step_with_adapter_metadata():
    plan = {
        "steps": [
            {"tool_name": "describe_agent_tools", "mutability": "read", "requires_confirmation": False},
            {"tool_name": "generate_chapter", "mutability": "write", "requires_confirmation": True},
        ]
    }
    metadata_by_name = build_approval_tool_metadata_by_name(
        plan,
        adapter_metadata_by_name={
            "generate_chapter": {
                "tool_name": "generate_chapter",
                "adapter_type": "static",
                "category": "generation",
                "mutability": "write",
                "handler_name": "_generate_chapter",
            }
        },
    )

    assert set(metadata_by_name) == {"generate_chapter"}
    assert metadata_by_name["generate_chapter"] == {
        "tool_name": "generate_chapter",
        "tool_exists": True,
        "adapter_exists": True,
        "adapter_type": "static",
        "handler_name": "_generate_chapter",
        "mutability": "write",
        "requires_confirmation": True,
        "required_fields": [],
    }


def test_approval_tool_metadata_reports_missing_adapter_for_known_write_step():
    metadata_by_name = build_approval_tool_metadata_by_name(
        {"steps": [{"tool_name": "generate_chapter", "mutability": "write", "requires_confirmation": True}]}
    )

    assert metadata_by_name["generate_chapter"] == {
        "tool_name": "generate_chapter",
        "tool_exists": True,
        "adapter_exists": False,
        "adapter_type": None,
        "handler_name": None,
        "mutability": "write",
        "requires_confirmation": True,
        "required_fields": [],
    }


def test_approval_tool_metadata_reports_missing_unknown_write_tool():
    metadata_by_name = build_approval_tool_metadata_by_name(
        {"steps": [{"tool_name": "unknown_writer", "mutability": "write", "requires_confirmation": True}]}
    )

    assert metadata_by_name["unknown_writer"] == {
        "tool_name": "unknown_writer",
        "tool_exists": False,
        "adapter_exists": False,
        "adapter_type": None,
        "handler_name": None,
        "mutability": "unclassified",
        "requires_confirmation": False,
        "required_fields": [],
    }


def test_approval_tool_metadata_ignores_read_only_steps():
    metadata_by_name = build_approval_tool_metadata_by_name(
        {"steps": [{"tool_name": "describe_agent_tools", "mutability": "read", "requires_confirmation": False}]}
    )

    assert metadata_by_name == {}
