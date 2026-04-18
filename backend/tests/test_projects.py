from app.models import (
    BackgroundTask,
    ChapterContent,
    ConsistencyCheck,
    Dialog,
    DialogMessage,
    ExtractedFact,
    Outline,
    PendingAction,
    PromptRule,
    Setup,
    Storyline,
    Topology,
    Version,
)


def test_create_and_get_project(client):
    r = client.post("/api/v1/projects", json={"name": "Test Novel"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Novel"
    pid = data["id"]

    r2 = client.get(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pid


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

    db_session.add_all([setup, storyline, outline, topology, chapter, check, fact, task, version, rule, dialog])
    db_session.commit()
    db_session.refresh(dialog)
    dialog_id = dialog.id

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
    assert db_session.query(Dialog).filter(Dialog.project_id == pid).count() == 0
    assert db_session.query(PendingAction).filter(PendingAction.dialog_id == dialog_id).count() == 0
    assert db_session.query(DialogMessage).filter(DialogMessage.dialog_id == dialog_id).count() == 0


def test_get_project_404(client):
    r = client.get("/api/v1/projects/nonexistent-id")
    assert r.status_code == 404
