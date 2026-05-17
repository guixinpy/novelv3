from sqlalchemy import event

from app.models import (
    BackgroundTask,
    ChapterContent,
    ChapterRevision,
    ConsistencyCheck,
    Dialog,
    DialogMessage,
    ExtractedFact,
    GenreProfile,
    Outline,
    PendingAction,
    Project,
    PromptRule,
    ProjectProfileVersion,
    RetrievalChunk,
    RetrievalDocument,
    RetrievalEmbedding,
    RetrievalTerm,
    RevisionAnnotation,
    RevisionCorrection,
    Setup,
    Storyline,
    Topology,
    Version,
    WorldCharacter,
    WorldRule,
    WritingState,
)
from app.services.writing.writing_state_service import WritingStateService


def test_create_and_get_project(client):
    r = client.post("/api/v1/projects", json={"name": "Test Novel"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Novel"
    pid = data["id"]

    r2 = client.get(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pid


def test_project_persists_target_chapter_count(client):
    r = client.post(
        "/api/v1/projects",
        json={"name": "Chapter Target Novel", "target_chapter_count": 10, "target_word_count": 30000},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["target_chapter_count"] == 10

    pid = data["id"]
    updated = client.patch(f"/api/v1/projects/{pid}", json={"target_chapter_count": 12})
    assert updated.status_code == 200
    assert updated.json()["target_chapter_count"] == 12

    fetched = client.get(f"/api/v1/projects/{pid}")
    assert fetched.status_code == 200
    assert fetched.json()["target_chapter_count"] == 12


def test_update_project_target_marks_writing_completed_when_pointer_is_beyond_target(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Retarget Short", "target_chapter_count": 10})
    pid = r.json()["id"]
    WritingStateService(db_session).run_chapter(pid, 6)

    response = client.patch(f"/api/v1/projects/{pid}", json={"target_chapter_count": 5})

    assert response.status_code == 200
    state = WritingStateService(db_session).state(pid)
    assert state.current_chapter == 6
    assert state.status == "completed"
    project = db_session.get(Project, pid)
    assert project.status == "completed"
    assert project.current_phase == "content"


def test_update_project_target_reopens_completed_writing_when_target_extends(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Retarget Long", "target_chapter_count": 1})
    pid = r.json()["id"]
    WritingStateService(db_session).complete_chapter(pid, 1)

    response = client.patch(f"/api/v1/projects/{pid}", json={"target_chapter_count": 3})

    assert response.status_code == 200
    state = WritingStateService(db_session).state(pid)
    assert state.current_chapter == 2
    assert state.status == "idle"
    project = db_session.get(Project, pid)
    assert project.status == "writing"
    assert project.current_phase == "content"


def test_list_projects(client):
    client.post("/api/v1/projects", json={"name": "Novel A"})
    client.post("/api/v1/projects", json={"name": "Novel B"})

    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    names = {p["name"] for p in data}
    assert names == {"Novel A", "Novel B"}
    assert data[0]["created_at"] >= data[1]["created_at"]


def test_list_projects_does_not_reconcile_chapter_word_counts(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Long Project"})
    pid = r.json()["id"]
    project = db_session.query(Project).filter(Project.id == pid).one()
    project.current_word_count = 123
    db_session.add_all([
        ChapterContent(
            project_id=pid,
            chapter_index=index,
            title=f"第{index}章",
            content="正文" * 100,
            word_count=1000,
            status="generated",
        )
        for index in range(1, 4)
    ])
    db_session.commit()
    statements: list[str] = []

    def capture_sql(_conn, _cursor, statement, _parameters, _context, _executemany):
        statements.append(" ".join(statement.lower().split()))

    event.listen(db_session.bind, "before_cursor_execute", capture_sql)
    try:
        response = client.get("/api/v1/projects")
    finally:
        event.remove(db_session.bind, "before_cursor_execute", capture_sql)

    assert response.status_code == 200
    listed = next(item for item in response.json() if item["id"] == pid)
    assert listed["current_word_count"] == 123
    assert all(
        "sum(" not in statement or "chapter_contents" not in statement
        for statement in statements
    )


def test_update_project(client):
    r = client.post("/api/v1/projects", json={"name": "Original"})
    pid = r.json()["id"]

    r2 = client.patch(f"/api/v1/projects/{pid}", json={"name": "Updated"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "Updated"


def test_delete_project(client):
    r = client.post("/api/v1/projects", json={"name": "To Delete"})
    pid = r.json()["id"]

    r2 = client.delete(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["deleted"] is True

    r3 = client.get(f"/api/v1/projects/{pid}")
    assert r3.status_code == 404


def test_delete_project_cleans_related_records(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Cascade Delete"})
    pid = r.json()["id"]

    setup = Setup(project_id=pid, status="generated")
    storyline = Storyline(project_id=pid, status="generated")
    outline = Outline(project_id=pid, status="generated")
    topology = Topology(project_id=pid)
    chapter = ChapterContent(project_id=pid, chapter_index=1, title="第1章", content="内容", word_count=2, status="generated")
    check = ConsistencyCheck(project_id=pid, chapter_index=1, checker_name="Checker", description="desc")
    fact = ExtractedFact(project_id=pid, chapter_index=1, type="character_presence")
    task = BackgroundTask(project_id=pid, task_type="generate_outline", status="completed")
    version = Version(project_id=pid, node_type="outline", node_id="outline-1", version_number=1, content="{}", description="v1")
    rule = PromptRule(project_id=pid, rule_type="style", condition="always", action="keep concise")
    dialog = Dialog(project_id=pid, state="pending_action")
    writing_state = WritingState(project_id=pid, current_chapter=12, status="running")

    db_session.add_all([setup, storyline, outline, topology, chapter, check, fact, task, version, rule, dialog, writing_state])
    db_session.commit()
    db_session.refresh(chapter)
    db_session.refresh(dialog)
    revision = ChapterRevision(project_id=pid, chapter_id=chapter.id, chapter_index=1, revision_index=1, status="submitted")
    db_session.add(revision)
    db_session.commit()
    db_session.refresh(revision)
    annotation = RevisionAnnotation(revision_id=revision.id, paragraph_index=0, start_offset=0, end_offset=1, selected_text="内", comment="改")
    correction = RevisionCorrection(revision_id=revision.id, paragraph_index=0, original_text="旧", corrected_text="新")
    db_session.add_all([annotation, correction])
    db_session.commit()
    dialog_id = dialog.id
    revision_id = revision.id

    pending = PendingAction(dialog_id=dialog_id, type="preview_outline")
    message = DialogMessage(dialog_id=dialog_id, role="assistant", content="确认要执行吗？")
    db_session.add_all([pending, message])
    db_session.commit()

    r2 = client.delete(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["deleted"] is True

    assert db_session.query(Setup).filter(Setup.project_id == pid).count() == 0
    assert db_session.query(Storyline).filter(Storyline.project_id == pid).count() == 0
    assert db_session.query(Outline).filter(Outline.project_id == pid).count() == 0
    assert db_session.query(Topology).filter(Topology.project_id == pid).count() == 0
    assert db_session.query(ChapterContent).filter(ChapterContent.project_id == pid).count() == 0
    assert db_session.query(ConsistencyCheck).filter(ConsistencyCheck.project_id == pid).count() == 0
    assert db_session.query(ExtractedFact).filter(ExtractedFact.project_id == pid).count() == 0
    assert db_session.query(BackgroundTask).filter(BackgroundTask.project_id == pid).count() == 0
    assert db_session.query(Version).filter(Version.project_id == pid).count() == 0
    assert db_session.query(PromptRule).filter(PromptRule.project_id == pid).count() == 0
    assert db_session.query(WritingState).filter(WritingState.project_id == pid).count() == 0
    assert db_session.query(ChapterRevision).filter(ChapterRevision.project_id == pid).count() == 0
    assert db_session.query(RevisionAnnotation).filter(RevisionAnnotation.revision_id == revision_id).count() == 0
    assert db_session.query(RevisionCorrection).filter(RevisionCorrection.revision_id == revision_id).count() == 0
    assert db_session.query(Dialog).filter(Dialog.project_id == pid).count() == 0
    assert db_session.query(PendingAction).filter(PendingAction.dialog_id == dialog_id).count() == 0
    assert db_session.query(DialogMessage).filter(DialogMessage.dialog_id == dialog_id).count() == 0


def test_delete_project_cleans_retrieval_index_records(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Delete Indexed Project"})
    pid = r.json()["id"]

    document = RetrievalDocument(
        project_id=pid,
        source_type="chapter",
        source_id="chapter-1",
        source_ref="chapter:1",
        title="第1章",
        chapter_index=1,
        content_hash="hash-1",
        document_metadata={},
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    chunk = RetrievalChunk(
        project_id=pid,
        document_id=document.id,
        chunk_index=0,
        text="旧灯塔熄灭时，亡者不能被直接召回。",
        token_count=12,
        start_offset=0,
        end_offset=18,
        chunk_metadata={},
    )
    db_session.add(chunk)
    db_session.commit()
    db_session.refresh(chunk)

    embedding = RetrievalEmbedding(
        project_id=pid,
        chunk_id=chunk.id,
        provider="local",
        model="hash-bigram-v1",
        dimensions=3,
        vector=[1.0, 0.0, 0.0],
        vector_hash="vector-hash-1",
    )
    term = RetrievalTerm(project_id=pid, chunk_id=chunk.id, token="灯塔")
    db_session.add_all([embedding, term])
    db_session.commit()

    r2 = client.delete(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["deleted"] is True

    assert db_session.query(RetrievalEmbedding).filter(RetrievalEmbedding.project_id == pid).count() == 0
    assert db_session.query(RetrievalTerm).filter(RetrievalTerm.project_id == pid).count() == 0
    assert db_session.query(RetrievalChunk).filter(RetrievalChunk.project_id == pid).count() == 0
    assert db_session.query(RetrievalDocument).filter(RetrievalDocument.project_id == pid).count() == 0


def test_delete_project_cleans_imported_world_model_records(client, db_session):
    r = client.post("/api/v1/projects", json={"name": "Delete Athena Profile"})
    pid = r.json()["id"]
    db_session.add(
        Setup(
            project_id=pid,
            status="generated",
            world_building={"rules": "旧灯塔熄灭时，亡者不能被直接召回。"},
            characters=[{"name": "林舟", "personality": "谨慎"}],
            core_concept={"theme": "记忆与真相"},
        )
    )
    db_session.commit()

    imported = client.post(f"/api/v1/projects/{pid}/athena/ontology/import-setup")
    assert imported.status_code == 200
    assert db_session.query(ProjectProfileVersion).filter(ProjectProfileVersion.project_id == pid).count() == 1
    assert db_session.query(WorldCharacter).filter(WorldCharacter.project_id == pid).count() == 1
    assert db_session.query(WorldRule).filter(WorldRule.project_id == pid).count() == 1

    r2 = client.delete(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["deleted"] is True

    assert db_session.query(ProjectProfileVersion).filter(ProjectProfileVersion.project_id == pid).count() == 0
    assert db_session.query(WorldCharacter).filter(WorldCharacter.project_id == pid).count() == 0
    assert db_session.query(WorldRule).filter(WorldRule.project_id == pid).count() == 0
    assert db_session.query(GenreProfile).filter(GenreProfile.canonical_id == f"project-setup-import.{pid}").count() == 0


def test_get_project_404(client):
    r = client.get("/api/v1/projects/nonexistent-id")
    assert r.status_code == 404
