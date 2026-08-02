"""arch-refactor 阶段 5 验证：连续写作 8 章（新架构长链行为验证）。

验证点：工具调用链、护栏（无误触发）、压缩（上下文增长）、记忆延续、字数稳定。

用法：cd backend && python ../scripts/dogfood_v2_run.py [章节数]
输出：每章字数/工具调用/护栏/压缩事件 + 汇总报告。
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy.orm import Session  # noqa: E402

from app.config import load_api_key  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import ChapterContent, Project, Setup  # noqa: E402
from core.events import Compaction, GuardTripped, ToolFinished, TurnEnded  # noqa: E402
from core.harness import AgentHarness, HarnessConfig  # noqa: E402
from core.providers.deepseek import DeepSeekProvider  # noqa: E402
from core.tools.base import ToolContext, ToolRegistry  # noqa: E402
from domain.memory.project_snapshot import build_project_snapshot  # noqa: E402
from domain.tools.memory_tools import register_memory_tools  # noqa: E402
from domain.tools.retrieval_tools import register_retrieval_tools  # noqa: E402
from domain.tools.writing_tools import register_writing_tools  # noqa: E402

SYSTEM_PROMPT = (
    "你是一位长篇网文创作助手，正在连载一部现代都市悬疑小说《雾城来信》。"
    "写作流程："
    "1. 每章用 plan_arc progress 检查弧线进度（第一章先 plan_arc define 第一卷 1-8 章）"
    "2. 用 write_chapter 把章节正文写入项目（正文不含章题行、无 markdown、全角标点）"
    "3. 写完用 check_chapter_format 自检，发现问题立即修正后重写"
    "4. 每章结束用 track_plotline 维护伏笔，用 query_memory 回顾设定"
    "主线：主角林舟在雾城收到亡父遗留的信件，调查一起旧案。每章 800-1200 字，章末留悬念。"
)


async def run(n_chapters: int) -> int:
    key = load_api_key()
    if not key:
        print("DeepSeek API key 未配置")
        return 1

    db: Session = SessionLocal()
    project = Project(name="dogfood-v2-8章")
    db.add(project)
    db.flush()
    db.add(Setup(
        project_id=project.id, status="generated",
        characters=[{"name": "林舟", "description": "主角，28岁，夜班出租车司机"}, {"name": "程砚秋", "description": "雾城刑警"}],
        world_building={"locations": ["雾城", "老码头", "档案室"], "rules": ["信件是唯一线索"]},
        core_concept={"tone": "冷峻悬疑，克制抒情"},
    ))
    db.commit()
    db.refresh(project)
    print(f"project: {project.id}，计划 {n_chapters} 章")

    registry = ToolRegistry()
    register_writing_tools(registry)
    register_memory_tools(registry)
    register_retrieval_tools(registry)
    session_id = uuid.uuid4().hex[:16]
    session_dir = Path("data/agent_sessions_v2") / session_id
    harness = AgentHarness(
        session_id=session_id,
        session_dir=session_dir,
        provider=DeepSeekProvider(api_key=key),
        registry=registry,
        tool_context=ToolContext(project_id=project.id, session_id=session_id, db=db, extras={"work_dir": str(session_dir / "artifacts")}),
        config=HarnessConfig(system_prompt=SYSTEM_PROMPT, max_iterations_per_turn=25, max_wall_clock_ms=900_000),
        snapshot_provider=lambda: build_project_snapshot(db, project.id),
    )

    # 汇总指标
    stats = {
        "guards": [], "compactions": [], "tool_errors": [],
        "tool_calls": 0, "turns": 0, "tokens_in": 0, "tokens_out": 0,
        "per_chapter": [],
    }

    for chapter_index in range(1, n_chapters + 1):
        print(f"\n=== 第 {chapter_index} 章 ===")
        chapter_events = {"tool_calls": 0, "errors": 0, "assistant_text": ""}
        async for event in harness.send(f"请写第 {chapter_index} 章。"):
            kind = event.kind.value
            if kind == "tool_started":
                chapter_events["tool_calls"] += 1
                stats["tool_calls"] += 1
                print(f"  [tool] {event.name}")
            elif kind == "tool_finished":
                if event.is_error:
                    chapter_events["errors"] += 1
                    stats["tool_errors"].append((chapter_index, event.name, event.error_code))
                    print(f"  [tool-err] {event.name}: {event.error_code}")
            elif kind == "guard_tripped":
                stats["guards"].append((chapter_index, event.level, event.reason[:80]))
                print(f"  [guard] L{event.level}: {event.reason[:80]}")
            elif kind == "compaction":
                stats["compactions"].append((chapter_index, event.before_count, event.after_count))
                print(f"  [compact] {event.before_count}→{event.after_count}")
            elif kind == "turn_ended":
                stats["turns"] += 1
                stats["tokens_in"] += event.prompt_tokens
                stats["tokens_out"] += event.completion_tokens
                print(f"  [turn-end] {event.stop_reason} iters={event.iterations} "
                      f"in={event.prompt_tokens} out={event.completion_tokens} detail={event.exit_detail}")
        chapter = (
            db.query(ChapterContent)
            .filter(ChapterContent.project_id == project.id, ChapterContent.chapter_index == chapter_index)
            .first()
        )
        if chapter is None:
            print(f"  !!! 第 {chapter_index} 章未生成")
            stats["per_chapter"].append({"chapter": chapter_index, "words": 0})
            continue
        stats["per_chapter"].append({"chapter": chapter_index, "words": chapter.word_count, "title": chapter.title})
        print(f"  [OK] Ch{chapter_index}《{chapter.title}》 {chapter.word_count}字")

    # 汇总报告
    print("\n" + "=" * 50)
    print("Dogfood 汇总（8 章连续写作）")
    print(f"  章节: {len(stats['per_chapter'])}（字数: {[c['words'] for c in stats['per_chapter']]}）")
    print(f"  工具调用: {stats['tool_calls']}，工具错误: {len(stats['tool_errors'])}")
    print(f"  护栏触发: {len(stats['guards'])} {stats['guards'] if stats['guards'] else '(无)'}")
    print(f"  压缩次数: {len(stats['compactions'])}")
    print(f"  tokens: in={stats['tokens_in']} out={stats['tokens_out']}")

    # 清理
    db.query(ChapterContent).filter(ChapterContent.project_id == project.id).delete()
    db.query(Setup).filter(Setup.project_id == project.id).delete()
    db.delete(project)
    db.commit()
    print("测试项目已清理")
    return 0


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    raise SystemExit(asyncio.run(run(n)))
