from app.services.writing_agent.agent_definitions import inspect_agent_definition_registry, load_agent_definition


def test_load_agent_definition_accepts_toml_format(tmp_path):
    (tmp_path / "drafting_worker.toml").write_text(
        """
name = "drafting_worker"
role = "worker"
max_depth = 0
allowed_tools = ["preflight_writing", "generate_chapter"]

[write_policy]
mode = "guarded_generation"
allow_writes = true
guarded_writes = "approval_required"
child_dispatch = "deny"
""".strip(),
        encoding="utf-8",
    )

    definition = load_agent_definition("drafting_worker", base_dir=tmp_path)

    assert definition["status"] == "ready"
    assert definition["source_format"] == "toml"
    assert definition["allowed_tools"] == ["preflight_writing", "generate_chapter"]
    assert definition["write_policy"]["child_dispatch"] == "deny"
    assert definition["can_dispatch_children"] is False


def test_agent_definition_registry_reports_source_format_for_worker_definitions():
    registry = inspect_agent_definition_registry()

    assert registry["status"] == "passed"
    assert {definition["source_format"] for definition in registry["definitions"]} == {"yaml"}
