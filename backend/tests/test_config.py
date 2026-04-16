from unittest.mock import patch


def test_get_config_no_key(client):
    with patch("app.api.config.load_api_key", return_value=None):
        r = client.get("/api/v1/config")
    assert r.status_code == 200
    assert r.json() == {"has_api_key": False}


def test_get_config_with_key(client):
    with patch("app.api.config.load_api_key", return_value="sk-test"):
        r = client.get("/api/v1/config")
    assert r.status_code == 200
    assert r.json() == {"has_api_key": True}


def test_update_config(client):
    with patch("app.api.config.save_api_key") as mock_save:
        r = client.put("/api/v1/config", json={"api_key": "sk-new-key"})
    assert r.status_code == 200
    assert r.json() == {"has_api_key": True}
    mock_save.assert_called_once_with("sk-new-key")
