import pytest

from app.services.writing_agent.memory_provenance_contract import build_memory_provenance


def test_build_memory_provenance_normalizes_required_contract_fields():
    provenance = build_memory_provenance(
        version="phase999.test_memory_provenance.v1",
        status="available",
        sources=[
            {
                "source_ref": "LongformMemory:chapter:1",
                "source_type": "longform_memory",
                "item_count": 2,
            }
        ],
        windows=None,
        recovery=None,
        trace={"source": "test_memory_route", "mutability": "read"},
        extras={
            "boundaries": {
                "world_truth": {
                    "status": "separated",
                    "canonical_source": "Athena/world_model",
                }
            }
        },
    )

    assert provenance == {
        "version": "phase999.test_memory_provenance.v1",
        "status": "available",
        "source_count": 1,
        "sources": [
            {
                "source_ref": "LongformMemory:chapter:1",
                "source_type": "longform_memory",
                "item_count": 2,
            }
        ],
        "windows": {},
        "recovery": {"status": "none", "reason": "available", "next_tools": [], "tools": []},
        "trace": {
            "source": "test_memory_route",
            "mutability": "read",
            "version": "phase999.test_memory_provenance.v1",
        },
        "boundaries": {
            "world_truth": {
                "status": "separated",
                "canonical_source": "Athena/world_model",
            }
        },
    }


def test_build_memory_provenance_rejects_missing_trace_source():
    with pytest.raises(ValueError, match="memory_provenance.trace.source"):
        build_memory_provenance(
            version="phase999.test_memory_provenance.v1",
            status="available",
            sources=[],
            windows={},
            recovery=None,
            trace={"mutability": "read"},
        )


def test_build_memory_provenance_rejects_malformed_source_entries():
    with pytest.raises(ValueError, match="memory_provenance.sources\\[0\\].source_ref"):
        build_memory_provenance(
            version="phase999.test_memory_provenance.v1",
            status="available",
            sources=[{"source_type": "longform_memory"}],
            windows={},
            recovery=None,
            trace={"source": "test_memory_route"},
        )
