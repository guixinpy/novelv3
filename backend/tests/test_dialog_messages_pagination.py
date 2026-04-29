from datetime import UTC, datetime, timedelta

from app.models import Dialog, DialogMessage, Project


def _project_with_messages(db_session, dialog_type="hermes"):
    project = Project(name="分页测试")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, dialog_type=dialog_type)
    db_session.add(dialog)
    db_session.flush()
    messages = []
    base = datetime(2026, 4, 29, tzinfo=UTC)
    for index, content in enumerate(["A", "B", "C"], start=1):
        message = DialogMessage(
            dialog_id=dialog.id,
            role="assistant",
            content=content,
            created_at=base + timedelta(seconds=index),
        )
        messages.append(message)
    db_session.add_all(messages)
    db_session.commit()
    return project, messages


def test_dialog_messages_limit_returns_latest_messages_in_ascending_order(client, db_session):
    project, _messages = _project_with_messages(db_session)

    response = client.get(f"/api/v1/dialog/projects/{project.id}/messages?limit=2")

    assert response.status_code == 200
    assert [item["content"] for item in response.json()] == ["B", "C"]


def test_dialog_messages_after_id_returns_newer_messages(client, db_session):
    project, messages = _project_with_messages(db_session)

    response = client.get(f"/api/v1/dialog/projects/{project.id}/messages?after_id={messages[0].id}")

    assert response.status_code == 200
    assert [item["content"] for item in response.json()] == ["B", "C"]


def test_athena_messages_forwards_pagination_params(client, db_session):
    project, _messages = _project_with_messages(db_session, dialog_type="athena")

    response = client.get(f"/api/v1/projects/{project.id}/athena/dialog/messages?limit=1")

    assert response.status_code == 200
    assert [item["content"] for item in response.json()] == ["C"]
