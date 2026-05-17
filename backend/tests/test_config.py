from unittest.mock import patch
from unittest.mock import AsyncMock

from app.config import load_api_key
from app.core.ai_service import AIService


def test_load_api_key_can_be_disabled_for_local_e2e(monkeypatch):
    monkeypatch.setenv("MOZHOU_DISABLE_API_KEY", "1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

    assert load_api_key() is None


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


def test_update_config_resets_cached_ai_adapters(client):
    service = AIService()
    adapter = AsyncMock()
    service._adapter = adapter

    with patch("app.api.config.save_api_key") as mock_save:
        r = client.put("/api/v1/config", json={"api_key": "sk-rotated-key"})

    assert r.status_code == 200
    mock_save.assert_called_once_with("sk-rotated-key")
    assert service._adapter is None
    adapter.close.assert_awaited_once()
