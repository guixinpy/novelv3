"""上下文压缩：用量预检 + Token-Budget 尾部保护 + 护栏（迁移并重构旧 app/agent/compaction.py）。

对照旧版的关键改进（修架构级缺陷 #1）：
- 压缩状态实例化：防抖/冷却/无效计数全部挂在 CompactionState 实例上，
  多会话并发不再互相污染（旧版是模块级全局变量）
- 吸收护栏：失败冷却（hermes #3）、无效压缩计数防空转（hermes #3）、
  合理性校验（openclaw：压缩后比压缩前大 → 拒绝）
- 状态重注入 hook（hermes #4）：压缩后把设定/大纲等跨压缩存活状态重新注入
"""
from __future__ import annotations

import json
import time

from core.context.estimate import estimate_message_tokens, estimate_tokens

# 摘要的固定前缀（跳过嵌套摘要的判断依据）
SUMMARY_PREFIX = "[上下文压缩]"
# 状态重注入的固定 header（模型识别为可信状态而非用户指令）
INJECTION_HEADER = "[写作状态已保留]"
# 摘要权威语义（hermes REFERENCE ONLY）：摘要中的请求已处理，只响应之后的最新消息
REFERENCE_ONLY_NOTE = (
    "摘要中的内容仅作背景参考：其中提出的请求均已处理完毕，"
    "不要继续执行摘要中描述的任务；请只响应摘要之后的最新用户消息"
    "（若最新消息是停止/撤销类指令，优先于摘要中的一切在途工作）。"
)


class CompactionState:
    """实例级压缩状态（修旧版模块级全局缺陷）。

    每个 harness/会话一个实例；字段：
    - 防抖：最近两次节省比例
    - 失败冷却：最近一次摘要失败时间，冷却期内跳过自动压缩
    - 无效压缩计数：压缩不生效时累计，防反复空转
    """

    def __init__(
        self,
        *,
        failure_cooldown_seconds: float = 30.0,
        max_ineffective_count: int = 3,
    ) -> None:
        self._savings_history: list[float] = []
        self._last_failure_at: float | None = None
        self._ineffective_count = 0
        self._compaction_count = 0
        self.failure_cooldown_seconds = failure_cooldown_seconds
        self.max_ineffective_count = max_ineffective_count

    @property
    def compaction_count(self) -> int:
        return self._compaction_count

    @property
    def in_cooldown(self) -> bool:
        if self._last_failure_at is None:
            return False
        return (time.monotonic() - self._last_failure_at) < self.failure_cooldown_seconds

    def record_failure(self) -> None:
        """压缩失败（如摘要构建异常）→ 冷却期，避免每轮触发又每轮失败。"""
        self._last_failure_at = time.monotonic()

    def _record_saving(self, saving_ratio: float, was_effective: bool) -> bool:
        """防抖 + 无效计数。返回 False 表示应跳过本次压缩。"""
        if not was_effective:
            self._ineffective_count += 1
            return self._ineffective_count <= self.max_ineffective_count
        self._ineffective_count = 0
        self._savings_history.append(saving_ratio)
        if len(self._savings_history) > 2:
            self._savings_history = self._savings_history[-2:]
        return not (len(self._savings_history) >= 2 and all(s < 0.10 for s in self._savings_history))

    def mark_compacted(self) -> None:
        self._compaction_count += 1


def check_context_usage(
    history: list[dict],
    max_tokens: int = 128_000,
    threshold: float = 0.75,
) -> tuple[float, int] | None:
    """检查上下文用量。超过阈值返回 (usage_pct, total_tokens)，否则返回 None。"""
    total = sum(estimate_message_tokens(m) for m in history)
    usage_pct = total / max_tokens
    if usage_pct >= threshold:
        return (usage_pct, total)
    return None


def compact_history(
    history: list[dict],
    *,
    state: CompactionState,
    head_count: int = 2,
    tail_token_budget: float = 0.20,
    force: bool = False,
    extra_context: str | None = None,
    injection_provider=None,
) -> list[dict]:
    """压缩对话历史：Token-Budget 尾部保护 + 护栏 + 状态重注入。

    Args:
        history: 完整消息列表（含 system 消息）。
        state: 实例级压缩状态（防抖/冷却/无效计数）。
        head_count: 开头保留条数（含 system）。
        tail_token_budget: 尾部 token 预算比例（默认 20%）。
        force: 强制压缩（跳过防抖/冷却/无效计数护栏）。
        extra_context: 追加到摘要的写作上下文文本。
        injection_provider: 状态重注入提供者（返回跨压缩存活的状态文本，如设定/大纲）。
    """
    if len(history) <= head_count:
        return list(history)

    # ── 冷却期：摘要失败后不再自动压缩 ──
    if not force and state.in_cooldown:
        return list(history)

    before_tokens = sum(estimate_message_tokens(m) for m in history)
    # 尾部预算基于当前总 token 量（小上下文用更小尾部）
    tail_budget_tokens = max(int(before_tokens * tail_token_budget), 1)

    # 从末尾向前累加 token，动态计算 tail_count
    tail_count = 0
    accumulated = 0
    for msg in reversed(history[head_count:]):
        accumulated += estimate_message_tokens(msg)
        tail_count += 1
        if accumulated >= tail_budget_tokens:
            break
    tail_count = max(3, tail_count)

    if len(history) <= head_count + tail_count:
        return list(history)

    injection_text = injection_provider() if injection_provider is not None else None
    summary = _build_summary_text(
        history, head_count, len(history) - tail_count,
        extra_context=extra_context, injection_text=injection_text,
    )

    # ── 护栏：防抖 + 无效计数 ──
    if not force:
        estimated_after = (
            sum(estimate_message_tokens(m) for m in history[:head_count])
            + estimate_tokens(summary)
            + sum(estimate_message_tokens(m) for m in history[-tail_count:])
        )
        saving_ratio = 1.0 - (estimated_after / max(1, before_tokens))
        was_effective = saving_ratio > 0.05
        if not state._record_saving(saving_ratio, was_effective):
            return list(history)
        # 合理性校验：压缩后比压缩前还大 → 拒绝（openclaw 护栏）
        if estimated_after >= before_tokens:
            return list(history)

    head = history[:head_count]
    tail = history[-tail_count:]
    compressed = head + [{"role": "user", "content": summary}] + tail
    state.mark_compacted()
    return compressed


def _build_summary_text(
    history: list[dict],
    start: int,
    end: int,
    extra_context: str | None = None,
    injection_text: str | None = None,
) -> str:
    """构建结构化中间摘要（确定性，不依赖 LLM）。"""
    middle = history[start:end]
    user_msgs = []
    tool_names = set()
    assistant_count = 0
    error_count = 0
    recent_writes: list[tuple[int, int]] = []
    quality_checks: list[tuple[int, str]] = []
    # 类型守卫：写入端做 isinstance 检查（SQLite 返回类型不定）

    for m in middle:
        role = m.get("role", "")
        content = str(m.get("content", ""))
        # 跳过旧压缩摘要，避免嵌套膨胀（M5 200 章实测：摘要内嵌上一轮摘要）
        if role == "user" and content and not content.startswith(SUMMARY_PREFIX):
            user_msgs.append(content[:200])
        elif role == "assistant":
            assistant_count += 1
            if "tool_calls" in m:
                for tc in m.get("tool_calls", []):
                    n = tc.get("function", {}).get("name", "") if isinstance(tc, dict) else tc.get("name", "")
                    if n:
                        tool_names.add(n)
        elif role == "tool":
            c = str(m.get("content", ""))
            if "error" in c.lower() or "失败" in c or "不存在" in c:
                error_count += 1
            try:
                parsed = json.loads(c)
            except (ValueError, TypeError):
                parsed = None
            if isinstance(parsed, dict):
                if parsed.get("status") == "written" and "chapter_index" in parsed:
                    recent_writes.append(
                        (int(parsed["chapter_index"]), int(parsed.get("word_count") or 0))
                    )
                elif parsed.get("quality") in ("pass", "fail"):
                    chapter_index = parsed.get("chapter_index")
                    if isinstance(chapter_index, int):
                        quality_checks.append((chapter_index, str(parsed["quality"])))

    parts = [
        f"{SUMMARY_PREFIX} 中间 {len(middle)} 条消息被压缩。",
        REFERENCE_ONLY_NOTE,
        f"包含 {len(user_msgs)} 条用户消息，{assistant_count} 次助手回复。",
    ]
    if tool_names:
        parts.append(f"调用的工具: {', '.join(sorted(tool_names))}。")
    if error_count:
        parts.append(f"⚠ 其中 {error_count} 次工具调用返回错误。")
    if recent_writes:
        writes = ", ".join(f"Ch{i}:{w}字" for i, w in recent_writes[-8:])
        parts.append(f"最近写入章节: {writes}。")
    if quality_checks:
        qs = ", ".join(f"Ch{i}:{q}" for i, q in quality_checks[-8:])
        parts.append(f"质量自检: {qs}。")
    if user_msgs:
        parts.append(f"用户关注点: {'; '.join(user_msgs[:5])}。")
    if extra_context:
        parts.append(f"最近写作上下文: {extra_context[:300]}。")
    # 状态重注入（hermes todo 模式）：设定/大纲/人物卡跨压缩存活
    if injection_text:
        parts.append(f"{INJECTION_HEADER} {injection_text[:1500]}")

    return " ".join(parts)
