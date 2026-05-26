from app.models import (
    ChapterContent,
    GenreProfile,
    Project,
    ProjectProfileVersion,
    Storyline,
    WorldProposalBundle,
    WorldProposalItem,
    WritingAgentRun,
    WritingAgentStep,
)
from app.services.writing_agent.agent_health_projection import inspect_agent_health_projection
from app.services.writing_agent.narrative_trend_projection import (
    NARRATIVE_TREND_PROJECTION_VERSION,
    inspect_narrative_trend_projection,
)


def test_narrative_trend_projection_reports_ready_when_no_trends(db_session):
    project = Project(name="Narrative Trend Ready")
    db_session.add(project)
    db_session.commit()

    projection = inspect_narrative_trend_projection(db_session, project.id)

    assert projection["version"] == NARRATIVE_TREND_PROJECTION_VERSION
    assert projection["status"] == "ready"
    assert projection["summary"] == {
        "style_drift_findings": 0,
        "world_model_contradictions": 0,
        "overdue_foreshadowing": 0,
        "pacing_risks_requiring_human_judgment": 0,
    }
    assert projection["recommended_next_tools"] == []


def test_narrative_trend_projection_aggregates_drift_contradictions_and_foreshadowing(db_session):
    project = _seed_project_with_chapter(db_session, latest_chapter=8)
    _seed_review_step(
        db_session,
        project.id,
        tool_name="review_chapter_quality",
        chapter_index=6,
        findings=[
            {
                "code": "character_profile_drift",
                "severity": "blocker",
                "message": "主角行动方式偏离设定。",
            }
        ],
    )
    contradiction_item = _seed_world_model_contradiction(db_session, project.id)
    storyline = Storyline(
        project_id=project.id,
        status="generated",
        plotlines=[],
        foreshadowing=[
            {
                "hint": "黑伞来源",
                "planted_chapter": 1,
                "resolved_chapter": 4,
                "status": "planted",
            }
        ],
    )
    db_session.add(storyline)
    db_session.commit()

    projection = inspect_narrative_trend_projection(db_session, project.id, chapter_index=8)

    assert projection["status"] == "watch"
    assert projection["summary"] == {
        "style_drift_findings": 1,
        "world_model_contradictions": 1,
        "overdue_foreshadowing": 1,
        "pacing_risks_requiring_human_judgment": 0,
    }
    assert projection["style_drift"]["findings"][0]["code"] == "character_profile_drift"
    assert projection["world_model"]["contradictions"] == [
        {
            "proposal_item_id": contradiction_item.id,
            "chapter_index": 5,
            "subject_ref": "char.lin",
            "predicate": "timeline_contradiction",
            "status": "pending",
        }
    ]
    assert projection["foreshadowing"]["overdue"][0]["hint"] == "黑伞来源"
    assert projection["recommended_next_tools"] == [
        "review_chapter_quality",
        "review_chapter_continuity",
        "review_world_model_proposals",
        "plan_chapter_revision",
    ]


def test_narrative_trend_projection_marks_pacing_as_human_judgment(db_session):
    project = _seed_project_with_chapter(db_session, latest_chapter=3)
    _seed_review_step(
        db_session,
        project.id,
        tool_name="review_chapter_quality",
        chapter_index=3,
        findings=[
            {
                "code": "pacing_sag",
                "severity": "warning",
                "message": "连续三章节奏拖慢，需要人工判断是否保留铺垫。",
            }
        ],
    )

    projection = inspect_narrative_trend_projection(db_session, project.id, chapter_index=3)

    assert projection["status"] == "needs_human_judgment"
    assert projection["pacing"] == {
        "status": "needs_human_judgment",
        "automation": "not_automated",
        "risks": [
            {
                "code": "pacing_sag",
                "chapter_index": 3,
                "tool_name": "review_chapter_quality",
                "message": "连续三章节奏拖慢，需要人工判断是否保留铺垫。",
                "resolution": "requires_human_judgment",
            }
        ],
    }
    assert projection["recommended_next_tools"] == ["review_chapter_quality", "plan_chapter_revision"]


def test_agent_health_projection_includes_narrative_trends(db_session):
    project = _seed_project_with_chapter(db_session, latest_chapter=8)
    _seed_review_step(
        db_session,
        project.id,
        tool_name="review_chapter_continuity",
        chapter_index=8,
        findings=[
            {
                "code": "identifier_semantic_drift",
                "severity": "warning",
                "message": "代号含义与前文解释不一致。",
            }
        ],
    )

    health = inspect_agent_health_projection(db_session, project.id, chapter_index=8)

    assert health["narrative_trends"]["status"] == "watch"
    assert any(item["code"] == "narrative_trend_watch" for item in health["diagnostics"])
    assert "review_chapter_continuity" in health["recommended_next_tools"]


def _seed_project_with_chapter(db_session, *, latest_chapter: int) -> Project:
    project = Project(name=f"Narrative Trend {latest_chapter}")
    db_session.add(project)
    db_session.flush()
    for chapter_index in range(1, latest_chapter + 1):
        db_session.add(
            ChapterContent(
                project_id=project.id,
                chapter_index=chapter_index,
                title=f"第{chapter_index}章",
                content="章节正文",
                status="completed",
            )
        )
    db_session.commit()
    return project


def _seed_review_step(
    db_session,
    project_id: str,
    *,
    tool_name: str,
    chapter_index: int,
    findings: list[dict],
) -> None:
    run = WritingAgentRun(project_id=project_id, goal="review", status="success", input={})
    db_session.add(run)
    db_session.flush()
    db_session.add(
        WritingAgentStep(
            run_id=run.id,
            project_id=project_id,
            step_index=1,
            tool_name=tool_name,
            status="success",
            input={"params": {"chapter_index": chapter_index}},
            output={
                "status": "blocked" if any(item.get("severity") == "blocker" for item in findings) else "ready",
                "chapter_index": chapter_index,
                "findings": findings,
                "finding_count": len(findings),
            },
            chapter_index=chapter_index,
        )
    )
    db_session.commit()


def _seed_world_model_contradiction(db_session, project_id: str) -> WorldProposalItem:
    genre = GenreProfile(
        canonical_id=f"trend-{project_id}",
        primary_alias="trend",
        display_name="Trend",
        contract_version="world.contract.v1",
    )
    db_session.add(genre)
    db_session.flush()
    profile = ProjectProfileVersion(
        project_id=project_id,
        genre_profile_id=genre.id,
        version=1,
        contract_version=genre.contract_version,
        profile_payload={},
    )
    db_session.add(profile)
    db_session.flush()
    bundle = WorldProposalBundle(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        bundle_status="pending",
        title="矛盾提案",
        created_by="test",
    )
    db_session.add(bundle)
    db_session.flush()
    item = WorldProposalItem(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        bundle_id=bundle.id,
        item_status="pending",
        claim_id="claim.trend.contradiction",
        chapter_index=5,
        subject_ref="char.lin",
        predicate="timeline_contradiction",
        object_ref_or_value={"value": "第5章时间线冲突"},
        claim_layer="truth",
        evidence_refs=["chapter:5"],
        authority_type="derived",
        confidence=0.7,
        notes="contradiction with previous timeline",
        contract_version=profile.contract_version,
        created_by="test",
    )
    db_session.add(item)
    db_session.commit()
    return item
