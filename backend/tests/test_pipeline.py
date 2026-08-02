"""写作管线测试：workflow 图机制 + 真实 worker（mock provider 驱动）。

覆盖：一次通过、修订循环（review fail → 重写）、修订上限、落库。
"""
from __future__ import annotations

import pytest

from app.models import ChapterContent, Project, Setup
from core.workflow.base import WorkflowStatus
from domain.writing.pipeline import ChapterPipeline

from tests.core.conftest import ScriptedProvider

_GOOD_CHAPTER = (
    "林舟推开档案室的门，灰尘在灯光里浮动。"
    "“你来了。”程砚秋头也不抬地说。"
    "他点了点头，在桌前坐下，翻开那封泛黄的信。"
    "信纸边缘有一枚纽扣，沾着干涸的暗色痕迹。"
    "窗外，雾城的雨正下得密。"
    "他把纽扣收进衣袋，转身走出门去，雨声里夹着一声极轻的叹息。"
)


def _bad_chapter() -> str:
    # 含 markdown 残留 + 备选词 → review 必 REVISE
    return _GOOD_CHAPTER + "他**握紧**了那封信，决定明天去码头/仓库看看。"


@pytest.fixture
def project(db_session):
    p = Project(name="pipeline 测试")
    db_session.add(p)
    db_session.flush()
    db_session.add(Setup(project_id=p.id, status="generated", characters=[], world_building={}, core_concept={}))
    db_session.commit()
    db_session.refresh(p)
    return p


async def _run_pipeline(db, project, script: list[dict], max_revisions: int = 2):
    provider = ScriptedProvider(script)
    pipeline = ChapterPipeline(provider, db, project.id, max_revisions=max_revisions, word_target=800)
    result = await pipeline.run(1)
    return result, provider


async def test_pipeline_approves_and_finalizes(db_session, project):
    result, provider = await _run_pipeline(db_session, project, [{"content": _GOOD_CHAPTER}])
    assert result.status == WorkflowStatus.FINALIZED
    assert result.revisions == 0
    # 落库
    chapter = db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id).first()
    assert chapter is not None
    assert chapter.chapter_index == 1
    assert "林舟" in chapter.content


async def test_pipeline_revise_loop_then_approve(db_session, project):
    """review fail（格式残留）→ 带理由重写 → 通过。"""
    result, provider = await _run_pipeline(db_session, project, [{"content": _bad_chapter()}, {"content": _GOOD_CHAPTER}])
    assert result.status == WorkflowStatus.FINALIZED
    assert result.revisions == 1
    # provenance：第二次 execute 记录修订轮次（可审计）
    execute_steps = [s for s in result.steps if s.kind.value == "execute"]
    assert len(execute_steps) == 2
    assert execute_steps[1].revisions == 1
    # review 记录修订理由（provenance）
    review_steps = [s for s in result.steps if s.kind.value == "review"]
    assert review_steps and "markdown" in str(review_steps[0].result)
    # 落库的是修订后版本（无 ** 残留）
    chapter = db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id).first()
    assert chapter is not None
    assert "**" not in chapter.content


async def test_pipeline_revision_cap_still_finalizes(db_session, project):
    """修订上限：一直 fail 也进入 finalize（openhuman maxed 语义）。"""
    result, provider = await _run_pipeline(db_session, project, [{"content": _bad_chapter()}, {"content": _bad_chapter()}, {"content": _bad_chapter()}], max_revisions=1)
    assert result.status == WorkflowStatus.FINALIZED
    assert result.revisions == 2  # 0,1 两次修订后达到上限
    # 最终版本仍落库（带残留但可读）
    chapter = db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id).first()
    assert chapter is not None


async def test_pipeline_plan_reads_outline(db_session, project):
    """plan worker 读取大纲章节摘要。"""
    from app.models import Outline

    db_session.add(
        Outline(
            project_id=project.id,
            status="generated",
            total_chapters=10,
            chapters=[{"chapter_index": 1, "title": "雾城来信", "summary": "林舟收到亡父信件"}],
        )
    )
    db_session.commit()
    result, provider = await _run_pipeline(db_session, project, [{"content": _GOOD_CHAPTER}])
    assert result.status == WorkflowStatus.FINALIZED
    # plan 结果在 provenance
    plan_steps = [s for s in result.steps if s.kind.value == "plan"]
    assert plan_steps and "亡父信件" in str(plan_steps[0].result)


async def test_pipeline_invokes_introspect_after_run(db_session, project):
    """09 触发点 1：pipeline 完成后调用自省回调（注入式，不消耗 provider 脚本）。"""
    calls = []

    async def introspect(chapter_index, result):
        calls.append((chapter_index, result.status))

    provider = ScriptedProvider([{"content": _GOOD_CHAPTER}])
    pipeline = ChapterPipeline(provider, db_session, project.id, word_target=800, introspect=introspect)
    result = await pipeline.run(1)
    assert result.status == WorkflowStatus.FINALIZED
    assert calls == [(1, WorkflowStatus.FINALIZED)]


async def test_pipeline_introspect_fail_open(db_session, project):
    """fail-open：自省回调抛错不阻塞章节流程（finalize 结果不受影响）。"""
    async def introspect(chapter_index, result):
        raise RuntimeError("自省炸了")

    provider = ScriptedProvider([{"content": _GOOD_CHAPTER}])
    pipeline = ChapterPipeline(provider, db_session, project.id, word_target=800, introspect=introspect)
    result = await pipeline.run(1)
    assert result.status == WorkflowStatus.FINALIZED
    # 章节正常落库
    chapter = db_session.query(ChapterContent).filter(ChapterContent.project_id == project.id).first()
    assert chapter is not None
