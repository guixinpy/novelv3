"""arch-refactor 阶段 2 验证：真实生成 1 章（新内核 harness + writing 工具 + DeepSeek）。

用法：cd backend && python ../scripts/dogfood_v2_gen.py
输出：章节落库结果、字数、工具调用记录、护栏/压缩事件。
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy.orm import Session  # noqa: E402

from app.config import load_api_key  # noqa: E402
from domain.memory.project_snapshot import build_project_snapshot  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import ChapterContent, Project, Setup  # noqa: E402
from core.harness import AgentHarness, HarnessConfig  # noqa: E402
from core.providers.deepseek import DeepSeekProvider  # noqa: E402
from core.tools.base import ToolContext, ToolRegistry  # noqa: E402
from domain.tools.writing_tools import register_writing_tools  # noqa: E402

SYSTEM_PROMPT = (
    "你是一位长篇网文创作助手。写作时用 write_chapter 工具把章节正文写入项目"
    "（正文不含章题行、不含 markdown 标记、全角标点、对话用全角引号）。"
    "写完一章后可用 check_chapter_format 自检，发现问题主动修正后重写。"
)


async def main() -> int:
    key = load_api_key()
    if not key:
        print("DeepSeek API key 未配置")
        return 1

    # 1. 测试项目
    db: Session = SessionLocal()
    project = Project(name="dogfood-v2验证")
    db.add(project)
    db.flush()
    db.add(Setup(project_id=project.id, status="generated", characters=[{"name": "林舟"}], world_building={}, core_concept={}))
    db.commit()
    db.refresh(project)
    print(f"project: {project.id}")

    # 2. harness
    registry = ToolRegistry()
    register_writing_tools(registry)
    session_id = uuid.uuid4().hex[:16]
    session_dir = Path("data/agent_sessions_v2") / session_id
    harness = AgentHarness(
        session_id=session_id,
        session_dir=session_dir,
        provider=DeepSeekProvider(api_key=key),
        registry=registry,
        tool_context=ToolContext(project_id=project.id, session_id=session_id, db=db, extras={"work_dir": str(session_dir / "artifacts")}),
        config=HarnessConfig(system_prompt=SYSTEM_PROMPT, max_iterations_per_turn=20, max_wall_clock_ms=600_000),
        snapshot_provider=lambda: build_project_snapshot(db, project.id),
    )

    # 3. 发送写作任务
    print("--- 生成中 ---")
    events = []
    async for event in harness.send("请写第一章（约 800 字）：林舟深夜回家，发现桌上留着一封信。悬念收尾。"):
        events.append(event)
        kind = event.kind.value
        if kind in ("tool_started", "tool_finished", "guard_tripped", "compaction", "turn_ended"):
            extra = {k: v for k, v in event.__dict__.items() if k != "kind" and v not in ("", None, [], {})}
            print(f"  [{kind}] {extra}")

    # 4. 结果
    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == 1)
        .first()
    )
    if chapter is None:
        print("!!! 未生成章节（模型未调用 write_chapter）")
        for e in events:
            if e.kind.value == "assistant_message":
                print(f"assistant: {e.content[:200]}")
        return 2

    print(f"--- 结果 ---")
    print(f"章节已落库: Ch{chapter.chapter_index}《{chapter.title}》 {chapter.word_count}字 status={chapter.status}")
    artifacts = list((session_dir / "artifacts" / "chapters").glob("*.md")) if (session_dir / "artifacts" / "chapters").exists() else []
    print(f"artifact 落盘: {[a.name for a in artifacts]}")
    transcript = session_dir / f"{session_id}.jsonl"
    print(f"转录: {transcript.name} ({transcript.stat().st_size} bytes)" if transcript.exists() else "转录缺失")

    # 清理：删除测试项目（先删关联子表，外键约束）
    db.query(ChapterContent).filter(ChapterContent.project_id == project.id).delete()
    db.query(Setup).filter(Setup.project_id == project.id).delete()
    db.delete(project)
    db.commit()
    print("测试项目已清理")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
