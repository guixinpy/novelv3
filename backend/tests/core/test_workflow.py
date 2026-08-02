"""工作流图机制测试：节点 worker 注入（确定性 mock）+ 修订循环 + 上限 + provenance。"""
from __future__ import annotations

from core.workflow.base import (
    ReviewCommand,
    ReviewVerdict,
    StepKind,
    WorkflowEngine,
    WorkflowStatus,
)


def make_engine(verdicts: list[ReviewCommand], *, max_revisions: int = 3, plan_fail: bool = False):
    async def plan(context):
        if plan_fail:
            raise RuntimeError("plan 失败")
        return {"outline": "大纲"}

    async def execute(context, reason):
        return {"chapter": f"正文 (rev: {reason or 'initial'})"}

    async def review(context, output):
        cmd = verdicts.pop(0) if verdicts else ReviewCommand.APPROVE
        return ReviewVerdict(command=cmd, reason="有情节漏洞" if cmd == ReviewCommand.REVISE else "")

    async def finalize(context, output):
        return {**output, "finalized": True}

    return WorkflowEngine(plan=plan, execute=execute, review=review, finalize=finalize, max_revisions=max_revisions)


async def test_approve_flow_finalizes():
    engine = make_engine([ReviewCommand.APPROVE])
    result = await engine.run({"project_id": "p1"})
    assert result.status == WorkflowStatus.FINALIZED
    assert result.revisions == 0
    kinds = [s.kind for s in result.steps]
    assert kinds == [StepKind.PLAN, StepKind.EXECUTE, StepKind.REVIEW, StepKind.FINALIZE]
    assert result.final_output["finalized"] is True


async def test_revise_loop_then_approve():
    engine = make_engine([ReviewCommand.REVISE, ReviewCommand.REVISE, ReviewCommand.APPROVE])
    result = await engine.run({})
    assert result.status == WorkflowStatus.FINALIZED
    assert result.revisions == 2
    # 修订理由传给 execute（可审计）
    execute_steps = [s for s in result.steps if s.kind == StepKind.EXECUTE]
    assert len(execute_steps) == 3
    assert "情节漏洞" in execute_steps[2].result["chapter"]


async def test_revision_cap_still_finalizes():
    """修订上限：maxed 仍进入 finalize（openhuman 语义）。"""
    engine = make_engine([ReviewCommand.REVISE] * 10, max_revisions=2)  # 永远 REVISE
    result = await engine.run({})
    assert result.status == WorkflowStatus.FINALIZED
    assert result.revisions == 3  # 0,1,2 三次修订后达到上限


async def test_provenance_records_prompt_and_result():
    engine = make_engine([ReviewCommand.APPROVE])
    result = await engine.run({})
    prov = result.provenance()
    assert len(prov) == 4
    assert all("result_summary" in p for p in prov)
    assert any(p["kind"] == "review" for p in prov)


async def test_worker_failure_returns_failed_status():
    engine = make_engine([ReviewCommand.APPROVE], plan_fail=True)
    result = await engine.run({})
    assert result.status == WorkflowStatus.FAILED
    assert "plan 失败" in result.error


async def test_checkpointer_called():
    """checkpoint：每 super-step 持久化（崩溃恢复基础）。"""
    checkpoints = []
    engine = make_engine([ReviewCommand.APPROVE])
    engine._checkpointer = lambda status, steps: checkpoints.append((status, len(steps)))
    result = await engine.run({})
    assert result.status == WorkflowStatus.FINALIZED
    assert checkpoints[-1][0] == WorkflowStatus.FINALIZED
    assert len(checkpoints) >= 4
