from datetime import UTC, datetime, timedelta

from app.models import Dialog, DialogMessage, Project


def _project_with_messages(db_session, dialog_type="hermes", count: int = 3):
    project = Project(name="分页测试")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, dialog_type=dialog_type)
    db_session.add(dialog)
    db_session.flush()
    messages = []
    base = datetime(2026, 4, 29, tzinfo=UTC)
    contents = ["A", "B", "C"] if count == 3 else [f"消息{index:03d}" for index in range(1, count + 1)]
    for index, content in enumerate(contents, start=1):
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


def test_dialog_messages_without_limit_returns_latest_default_page(client, db_session):
    project, _messages = _project_with_messages(db_session, count=250)

    response = client.get(f"/api/v1/dialog/projects/{project.id}/messages")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 80
    assert payload[0]["content"] == "消息171"
    assert payload[-1]["content"] == "消息250"


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


def test_dialog_messages_after_id_uses_id_tie_breaker_for_same_timestamp(client, db_session):
    project = Project(name="同时间分页测试")
    db_session.add(project)
    db_session.flush()
    dialog = Dialog(project_id=project.id, dialog_type="hermes")
    db_session.add(dialog)
    db_session.flush()
    created_at = datetime(2026, 4, 30, tzinfo=UTC)
    messages = [
        DialogMessage(id="msg-1", dialog_id=dialog.id, role="assistant", content="A", created_at=created_at),
        DialogMessage(id="msg-2", dialog_id=dialog.id, role="assistant", content="B", created_at=created_at),
        DialogMessage(id="msg-3", dialog_id=dialog.id, role="assistant", content="C", created_at=created_at),
    ]
    db_session.add_all(messages)
    db_session.commit()

    response = client.get(f"/api/v1/dialog/projects/{project.id}/messages?after_id=msg-1")

    assert response.status_code == 200
    assert [item["content"] for item in response.json()] == ["B", "C"]


def test_dialog_messages_after_id_returns_earliest_new_page(client, db_session):
    project, messages = _project_with_messages(db_session, count=101)

    response = client.get(f"/api/v1/dialog/projects/{project.id}/messages?after_id={messages[0].id}&limit=20")

    assert response.status_code == 200
    assert [item["content"] for item in response.json()] == [f"消息{index:03d}" for index in range(2, 22)]


def test_athena_messages_forwards_pagination_params(client, db_session):
    project, _messages = _project_with_messages(db_session, dialog_type="athena")

    response = client.get(f"/api/v1/projects/{project.id}/athena/dialog/messages?limit=1")

    assert response.status_code == 200
    assert [item["content"] for item in response.json()] == ["C"]
