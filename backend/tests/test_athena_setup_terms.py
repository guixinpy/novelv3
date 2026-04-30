from types import SimpleNamespace

from app.core.athena_setup_terms import extract_setup_world_terms


def test_extract_setup_world_terms_normalizes_phrase_like_locations_and_factions():
    setup = SimpleNamespace(
        world_building={
            "background": "故事发生在沿海城市‘澜城’，其灯塔区近期发生集体失忆事件。",
            "geography": "澜城分为旧城区、新开发区和灯塔区。灯塔区位于城市北端半岛，以一座废弃的百年灯塔为中心，周围是渔港改造的居民区和废弃工厂。",
            "society": "政府设立记忆管理局，守夜人联盟负责巡查旧城。",
            "atmosphere": "海雾时常笼罩灯塔区。",
        },
        core_concept={
            "premise": "唯一的线索是一段关于灯塔的模糊影像。",
        },
    )

    terms = extract_setup_world_terms(setup)

    location_names = {term["name"] for term in terms["locations"]}
    faction_names = {term["name"] for term in terms["factions"]}

    assert {"澜城", "旧城区", "新开发区", "灯塔区", "北端半岛", "灯塔", "渔港"}.issubset(location_names)
    assert "记忆管理局" in faction_names
    assert "守夜人联盟" in faction_names
    assert "沿海城市" not in location_names
    assert "其灯塔" not in location_names
    assert "城市北端半岛" not in location_names
    assert "周围是渔港" not in location_names
    assert "一段关于灯塔" not in location_names
    assert "海雾时常笼罩灯塔" not in location_names
    assert "以一座废弃的百年灯塔" not in location_names
    assert "政府设立记忆管理局" not in faction_names
