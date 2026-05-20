from app.core.world_contracts import DERIVED
from app.core.world_proposal_service import create_bundle, write_candidate_fact
from app.models import GenreProfile, Project, ProjectProfileVersion, WorldFactClaim
from app.schemas.world_proposals import ProposalCandidateFactCreate
from app.services.writing_agent.agent_world_model_route import inspect_agent_world_model_route


def test_inspect_agent_world_model_route_blocks_without_profile(db_session):
    project = Project(name="World Route Missing Profile")
    db_session.add(project)
    db_session.commit()

    output = inspect_agent_world_model_route(db_session, project.id, chapter_index=1)

    assert output["status"] == "completed"
    assert output["route"]["status"] == "blocked"
    assert output["route"]["reason"] == "missing_world_model_profile"
    assert output["recommended_actions"] == ["import_setup_world_model"]
    assert output["profile"] is None


def test_inspect_agent_world_model_route_reports_ready_subject_facts(db_session):
    project = _seed_profiled_project(db_session, "World Route Ready")
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).one()
    db_session.add(
        WorldFactClaim(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.hero.identity",
            chapter_index=1,
            subject_ref="char.hero",
            predicate="identity",
            object_ref_or_value="灯塔区调查员",
            claim_layer="truth",
            claim_status="confirmed",
            evidence_refs=["chapter:1"],
            authority_type=DERIVED,
            confidence=0.95,
            contract_version=profile.contract_version,
        )
    )
    db_session.commit()

    output = inspect_agent_world_model_route(
        db_session,
        project.id,
        chapter_index=2,
        subject_ref="char.hero",
    )

    assert output["status"] == "completed"
    assert output["route"]["status"] == "ready"
    assert output["route"]["reason"] == "world_model_ready"
    assert output["fact_summary"]["total_confirmed_facts"] == 1
    assert output["fact_summary"]["returned_facts"] == 1
    assert output["facts"][0]["subject_ref"] == "char.hero"
    assert output["facts"][0]["predicate"] == "identity"
    assert output["recommended_actions"] == ["preflight_writing"]


def test_inspect_agent_world_model_route_blocks_on_pending_proposals(db_session):
    project = _seed_profiled_project(db_session, "World Route Pending Proposals")
    profile = db_session.query(ProjectProfileVersion).filter_by(project_id=project.id).one()
    bundle = create_bundle(
        db=db_session,
        project_id=project.id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        created_by="athena.test",
        title="待审身份事实",
    )
    write_candidate_fact(
        db=db_session,
        bundle_id=bundle.id,
        created_by="athena.test",
        candidate=ProposalCandidateFactCreate(
            project_id=project.id,
            project_profile_version_id=profile.id,
            profile_version=profile.version,
            claim_id="claim.hero.role.pending",
            chapter_index=1,
            subject_ref="char.hero",
            predicate="role",
            object_ref_or_value="雾港调查者",
            claim_layer="truth",
            evidence_refs=["chapter:1"],
            authority_type=DERIVED,
            confidence=0.9,
            contract_version=profile.contract_version,
        ),
    )
    db_session.commit()

    output = inspect_agent_world_model_route(db_session, project.id, chapter_index=2)

    assert output["status"] == "completed"
    assert output["route"]["status"] == "blocked"
    assert output["route"]["reason"] == "pending_world_model_proposals"
    assert output["proposal_pressure"]["total_items"] == 1
    assert "review_world_model_proposals" in output["recommended_actions"]


def _seed_profiled_project(db_session, name: str) -> Project:
    project = Project(name=name)
    genre_profile = GenreProfile(
        canonical_id=f"{name.lower().replace(' ', '-')}-profile",
        display_name=name,
        contract_version="world.contract.v1",
    )
    db_session.add_all([project, genre_profile])
    db_session.commit()
    db_session.add(
        ProjectProfileVersion(
            project_id=project.id,
            genre_profile_id=genre_profile.id,
            version=1,
            contract_version="world.contract.v1",
            profile_payload={},
        )
    )
    db_session.commit()
    return project
