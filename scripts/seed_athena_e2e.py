#!/usr/bin/env python3
"""Seed deterministic Athena E2E data into the local test database."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.db import SessionLocal
from app.models import ChapterContent, Project, Setup


def seed(project_id: str) -> None:
    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise SystemExit(f"Project not found: {project_id}")

        setup = db.query(Setup).filter(Setup.project_id == project_id).first()
        setup_payload = {
            "world_building": {
                "background": "雾港城被潮雾笼罩。",
                "geography": "故事发生在‘旧灯塔’和‘雾港城’，旧灯塔地下藏有‘黑潮门’。",
                "society": "‘档案局’封存证词。",
                "rules": "旧灯塔熄灭时，亡者不能被直接召回。",
            },
            "characters": [
                {
                    "name": "林舟",
                    "personality": "谨慎",
                    "background": "雾港守夜人",
                    "goals": "查清旧灯塔失火真相",
                    "character_status": "alive",
                }
            ],
            "core_concept": {"theme": "记忆与真相", "hook": "旧灯塔会篡改证词"},
            "status": "generated",
        }
        if setup is None:
            setup = Setup(project_id=project_id, **setup_payload)
            db.add(setup)
        else:
            for key, value in setup_payload.items():
                setattr(setup, key, value)

        chapter = (
            db.query(ChapterContent)
            .filter(
                ChapterContent.project_id == project_id,
                ChapterContent.chapter_index == 1,
            )
            .first()
        )
        chapter_payload = {
            "title": "第一章 灯塔",
            "content": "林舟走进雾港城。旧灯塔重新点亮。档案局封锁街区，黑潮门在旧灯塔地下低鸣。",
            "word_count": 38,
            "status": "generated",
        }
        if chapter is None:
            chapter = ChapterContent(project_id=project_id, chapter_index=1, **chapter_payload)
            db.add(chapter)
        else:
            for key, value in chapter_payload.items():
                setattr(chapter, key, value)

        project.status = "writing"
        project.current_phase = "content"
        project.current_word_count = chapter_payload["word_count"]
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: seed_athena_e2e.py <project_id>")
    seed(sys.argv[1])
