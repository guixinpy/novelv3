"""工作流图机制（吸收 openhuman delegation.rs 的轻量版）。

plan → execute ⇄ review → finalize durable 图：

    plan ─▶ execute ─▶ review ──approved/maxed──▶ finalize ─▶ END
              ▲                   │
              └─────revise────────┘

设计要点：
- 节点 worker 注入：机制与真实 agent 解耦（测试注入确定性 mock，生产注入真实实现）
- 条件路由：review 返回 Command（approve / revise(reason)）
- 修订递归上限：max_revisions + 状态内计数器双保险
- per-step provenance：每步 prompt+result 逐条记录（可审计、可回滚）
- checkpoint 可选：每 super-step 调用 checkpointer（持久化恢复）

小说映射：大纲 → 撰写 → 评审（一致性/格式/文风）⇄ 修订 → 定稿。
本机制领域无关，任何题材的写作流程同构。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable


class StepKind(str, Enum):
    PLAN = "plan"
    EXECUTE = "execute"
    REVIEW = "review"
    FINALIZE = "finalize"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    FINALIZED = "finalized"
    FAILED = "failed"


class ReviewCommand(str, Enum):
    """review 节点的条件路由输出。"""

    APPROVE = "approve"
    REVISE = "revise"


@dataclass(frozen=True)
class ReviewVerdict:
    command: ReviewCommand
    reason: str = ""          # REVISE 时的修订理由（回传给 execute 节点）
    issues: list[str] = field(default_factory=list)


@dataclass
class StepRecord:
    """per-step provenance：每步的确切 prompt 与结果。"""

    index: int
    kind: StepKind
    prompt: str
    result: Any
    revisions: int = 0


@dataclass
class WorkflowResult:
    status: WorkflowStatus
    steps: list[StepRecord]
    final_output: Any = None
    revisions: int = 0
    error: str = ""

    def provenance(self) -> list[dict]:
        return [
            {
                "index": s.index,
                "kind": s.kind.value,
                "prompt": s.prompt[:500],
                "result_summary": str(s.result)[:300] if s.result is not None else "",
                "revisions": s.revisions,
            }
            for s in self.steps
        ]


# 节点 worker 签名（全部注入，机制本身无领域依赖）
PlanWorker = Callable[[dict], Awaitable[Any] | Any]          # context → plan 结果
ExecuteWorker = Callable[[dict, str], Awaitable[Any] | Any]  # (context, 上轮结果/修订理由) → 产出
ReviewWorker = Callable[[dict, Any], Awaitable[ReviewVerdict] | ReviewVerdict]  # (context, 产出) → 裁定
FinalizeWorker = Callable[[dict, Any], Awaitable[Any] | Any]  # (context, 定稿产出) → 终结果
Checkpointer = Callable[[WorkflowStatus, list[StepRecord]], Any]


class WorkflowEngine:
    """4 节点线性图 + 修订循环。节点 worker 全部注入，可确定性测试。"""

    def __init__(
        self,
        *,
        plan: PlanWorker,
        execute: ExecuteWorker,
        review: ReviewWorker,
        finalize: FinalizeWorker,
        max_revisions: int = 3,
        checkpointer: Checkpointer | None = None,
    ) -> None:
        self._plan = plan
        self._execute = execute
        self._review = review
        self._finalize = finalize
        self.max_revisions = max_revisions
        self._checkpointer = checkpointer

    async def run(self, context: dict) -> WorkflowResult:
        steps: list[StepRecord] = []
        revisions = 0

        async def checkpoint(status: WorkflowStatus) -> None:
            cp = self._checkpointer
            if cp is not None:
                await _maybe_await(cp(status, steps))

        try:
            await checkpoint(WorkflowStatus.RUNNING)

            # ── plan ──
            plan_result = await _maybe_await(self._plan(context))
            steps.append(StepRecord(index=len(steps), kind=StepKind.PLAN, prompt="", result=plan_result))
            await checkpoint(WorkflowStatus.RUNNING)

            # ── execute ⇄ review（修订循环，上限 max_revisions）──
            output: Any = plan_result
            reason = ""
            while True:
                execute_prompt = f"execute round (revision {revisions})" if revisions else "execute initial"
                output = await _maybe_await(self._execute(context, reason if revisions else ""))
                steps.append(
                    StepRecord(index=len(steps), kind=StepKind.EXECUTE, prompt=execute_prompt, result=output, revisions=revisions)
                )
                await checkpoint(WorkflowStatus.RUNNING)

                verdict = await _maybe_await(self._review(context, output))
                steps.append(
                    StepRecord(
                        index=len(steps), kind=StepKind.REVIEW,
                        prompt=verdict.command.value,
                        result={"command": verdict.command.value, "reason": verdict.reason, "issues": verdict.issues},
                        revisions=revisions,
                    )
                )
                await checkpoint(WorkflowStatus.RUNNING)

                if verdict.command == ReviewCommand.APPROVE:
                    break
                revisions += 1
                if revisions > self.max_revisions:
                    # 达到修订上限：带最后理由进入 finalize（openhuman：maxed 仍 finalize）
                    reason = verdict.reason
                    break
                reason = verdict.reason

            # ── finalize ──
            final_output = await _maybe_await(self._finalize(context, output))
            steps.append(
                StepRecord(index=len(steps), kind=StepKind.FINALIZE, prompt="finalize", result=final_output, revisions=revisions)
            )
            await checkpoint(WorkflowStatus.FINALIZED)

            return WorkflowResult(
                status=WorkflowStatus.FINALIZED,
                steps=steps,
                final_output=final_output,
                revisions=revisions,
            )
        except Exception as exc:  # noqa: BLE001 - 工作流失败以结果形式返回，不炸调用方
            await checkpoint(WorkflowStatus.FAILED)
            return WorkflowResult(status=WorkflowStatus.FAILED, steps=steps, error=str(exc))


async def _maybe_await(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value
