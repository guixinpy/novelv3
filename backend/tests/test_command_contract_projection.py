from app.services.writing_agent.command_contract_projection import (
    COMMAND_CONTRACTS_SOURCE,
    command_contracts_from_run_input,
)


def test_command_contracts_from_run_input_returns_bounded_summary():
    output = command_contracts_from_run_input(
        {
            "planner": {
                "trace": {
                    "agent_health_projection": {
                        "command_contracts": {
                            "status": "completed",
                            "summary": {
                                "total_commands": 8,
                                "public_commands": 5,
                                "agent_control_commands": 2,
                                "available_commands": 5,
                                "gap_count": 1,
                            },
                            "commands": [{"name": "continue"}],
                        }
                    }
                }
            }
        }
    )

    assert output == {
        "source": COMMAND_CONTRACTS_SOURCE,
        "summary": {
            "total_commands": 8,
            "public_commands": 5,
            "agent_control_commands": 2,
            "available_commands": 5,
            "gap_count": 1,
        },
    }


def test_command_contracts_from_run_input_returns_none_without_summary():
    assert command_contracts_from_run_input({}) is None
    assert command_contracts_from_run_input({"planner": {"trace": {"agent_health_projection": {}}}}) is None
