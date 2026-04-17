def test_get_default_preferences(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    r2 = client.get(f"/api/v1/projects/{pid}/preferences")
    assert r2.status_code == 200
    assert r2.json()["config"]["description_density"] == 3


def test_update_preferences(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    r2 = client.put(f"/api/v1/projects/{pid}/preferences", json={
        "description_density": 5,
        "dialogue_ratio": 1,
        "pacing_speed": 4,
        "tone_preferences": ["dark", "suspense"],
    })
    assert r2.status_code == 200
    assert r2.json()["config"]["description_density"] == 5

    r3 = client.get(f"/api/v1/projects/{pid}/preferences")
    assert r3.json()["config"]["tone_preferences"] == ["dark", "suspense"]


def test_reset_preferences(client):
    r = client.post("/api/v1/projects", json={"name": "Test"})
    pid = r.json()["id"]
    client.put(f"/api/v1/projects/{pid}/preferences", json={"description_density": 5})
    r2 = client.post(f"/api/v1/projects/{pid}/preferences/reset")
    assert r2.status_code == 200
    assert r2.json()["config"]["description_density"] == 3


def test_prompt_optimizer():
    from app.core.prompt_optimizer import PromptOptimizer
    opt = PromptOptimizer()
    result = opt.optimize("写一章", {"description_density": 5, "tone_preferences": ["dark"]})
    assert "感官细节" in result
    assert "压抑" in result

    result2 = opt.optimize("写一章", {"description_density": 3})
    assert "【用户偏好规则】" not in result2


def test_few_shot_library():
    from app.core.few_shot_library import FewShotExampleLibrary
    lib = FewShotExampleLibrary()
    examples = lib.select_examples("chapter", "末世")
    assert len(examples) >= 1
    formatted = lib.format_for_prompt(examples)
    assert "参考示例" in formatted
