"""Seed test project and data for M1 dogfood verification."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))
import httpx
from app.db import SessionLocal
from app.models import (
    ChapterContent, Project, Setup,
    WorldCharacter, WorldLocation,
    ProjectProfileVersion, GenreProfile,
)
from app.models.genre_profile import get_official_genre_profile_definition

BASE = "http://localhost:8000"

# 1. Create project via API
r = httpx.post(f"{BASE}/api/v1/projects", json={"name": "M1狗食测试", "genre": "悬疑"})
project = r.json()
pid = project["id"]
print(f"Project created: {pid}")

# 2. Seed data directly via DB
db = SessionLocal()
try:
    # 2a. Create GenreProfile for "mystery" if not exist
    genre_def = get_official_genre_profile_definition("mystery")
    gp = db.query(GenreProfile).filter(GenreProfile.canonical_id == "mystery").first()
    if gp is None:
        gp = GenreProfile(**genre_def.to_model_kwargs())
        db.add(gp)
        db.flush()
    print(f"GenreProfile: {gp.id} ({gp.display_name})")

    # 2b. Create ProjectProfileVersion
    ppv = ProjectProfileVersion(
        project_id=pid,
        genre_profile_id=gp.id,
        version=1,
        contract_version="world.contract.v1",
        profile_payload=genre_def.to_model_kwargs(),
    )
    db.add(ppv)
    db.flush()
    print(f"ProjectProfileVersion: v{ppv.version}")

    # 2c. Setup (world building + characters as JSON)
    setup = Setup(
        project_id=pid,
        world_building={
            "background": "雾港城被潮雾笼罩。旧灯塔是城市的精神象征。",
            "geography": "故事在旧灯塔和雾港城之间展开。旧灯塔地下藏有黑潮门。",
            "society": "档案局封存所有与灯塔有关的证词。市民分为两派。",
            "rules": "旧灯塔熄灭时，亡者不能被召回。潮雾中记忆模糊。",
        },
        characters=[
            {"name":"林舟","personality":"谨慎敏锐","background":"雾港守夜人",
             "goals":"查清灯塔失火真相","character_status":"alive"},
            {"name":"林思","personality":"理性果敢","background":"档案局调查员",
             "goals":"保护档案局秘密","character_status":"alive"},
        ],
        core_concept={"theme":"记忆与真相","hook":"旧灯塔会篡改证词"},
        status="generated",
    )
    db.add(setup)

    # 2d. World characters
    chars = [
        WorldCharacter(project_id=pid, profile_version=1,
            character_id=f"char-{pid}-linzhou",
            canonical_id=f"char-{pid}-linzhou",
            name="林舟", primary_alias="林舟",
            role_type="protagonist", identity_anchor="protagonist_林舟",
            contract_version="world.contract.v1",
            origin_background="雾港守夜人，32岁，父亲在灯塔火灾中失踪",
            core_traits=["谨慎","敏锐"],
            notes="林思的哥哥，正在调查旧灯塔失火真相"),
        WorldCharacter(project_id=pid, profile_version=1,
            character_id=f"char-{pid}-linsi",
            canonical_id=f"char-{pid}-linsi",
            name="林思", primary_alias="林思",
            role_type="supporting", identity_anchor="supporting_林思",
            contract_version="world.contract.v1",
            origin_background="档案局调查员，28岁，林舟的妹妹",
            core_traits=["理性","果敢"],
            notes="知道档案局内部的秘密，对哥哥的调查态度矛盾"),
    ]
    for c in chars:
        db.add(c)

    # 2e. World locations
    locs = [
        WorldLocation(project_id=pid, profile_version=1,
            location_id=f"loc-{pid}-lighthouse",
            canonical_id=f"loc-{pid}-lighthouse",
            name="旧灯塔", primary_alias="旧灯塔",
            location_type="建筑", contract_version="world.contract.v1",
            spatial_scope="point", functional_tags=["地标","入口"],
            hazards=["黑潮门在地下深处"]),
        WorldLocation(project_id=pid, profile_version=1,
            location_id=f"loc-{pid}-archive",
            canonical_id=f"loc-{pid}-archive",
            name="档案局", primary_alias="档案局",
            location_type="机构", contract_version="world.contract.v1",
            spatial_scope="point", functional_tags=["办公","封存"],
            access_constraints=["仅限内部人员进入"]),
    ]
    for l in locs:
        db.add(l)

    # 2f. Chapters
    db.add(ChapterContent(project_id=pid, chapter_index=1,
        title="第一章 灯塔",
        content="林舟走进雾港城。旧灯塔重新点亮。档案局封锁街区，黑潮门在旧灯塔地下低鸣。林思站在档案局门口，看着哥哥的背影消失在潮雾中。",
        word_count=56, status="generated"))
    db.add(ChapterContent(project_id=pid, chapter_index=3,
        title="第三章 迷雾",
        content="林舟在档案局的地下室发现了父亲留下的笔记。笔记中提到黑潮门需要三把钥匙才能打开。林思突然出现在楼梯口，表情复杂。",
        word_count=52, status="generated"))

    # 2g. Update project status
    p = db.query(Project).filter(Project.id == pid).first()
    p.status = "writing"
    p.current_phase = "content"
    p.current_word_count = 108
    db.commit()
    print("✅ Seed data committed successfully")
finally:
    db.close()

# 3. Verify
r = httpx.get(f"{BASE}/api/v1/projects/{pid}")
print(f"Project GET: {r.status_code}")
r = httpx.get(f"{BASE}/api/v1/chapters?project_id={pid}")
chapters = r.json()
print(f"Chapters: {len(chapters)}")

print(f"\n✅ Done. Project ID: {pid}")
print(f"   Next: POST {BASE}/api/v2/sessions with project_id={pid}")
