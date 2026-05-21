# Phase97 Agent Tool Policy Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 Writing Agent 运行服务中残留的报告类工具停止策略抽离为独立、可测试的 Agent tool policy 合约。

**Architecture:** `run_service.py` 继续负责运行步骤和状态落库；新增 `tool_policy.py` 负责工具级报告阻断、允许的后继工具和阻断提示文案。此阶段不改变工具执行语义，只把策略从运行编排中解耦，便于后续把策略暴露给 planner、UI 和 Trace。

**Tech Stack:** FastAPI backend, pytest, Python service modules.

---

### Task 1: 写策略模块 RED 测试

**Files:**
- Create: `backend/tests/test_writing_agent_tool_policy.py`

- [ ] **Step 1: 写失败测试**

```python
from app.services.writing_agent.tool_policy import (
    allowed_report_followup,
    should_stop_after_report,
    successful_report_block_message,
)


def test_agent_tool_policy_blocks_report_tools_until_allowed_followup():
    assert should_stop_after_report(
        "seed_continuity_anchor_proposals",
        {"should_generate_next_chapter": False},
        step_index=0,
        total_steps=2,
        next_tool_name="generate_chapter",
    ) is True
    assert should_stop_after_report(
        "seed_continuity_anchor_proposals",
        {"should_generate_next_chapter": False},
        step_index=0,
        total_steps=2,
        next_tool_name="apply_world_model_proposal_resolution",
    ) is False
    assert allowed_report_followup(
        "seed_continuity_anchor_proposals",
        "apply_world_model_proposal_resolution",
    ) is True
```

- [ ] **Step 2: 运行 RED**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py -q`
Expected: FAIL，因为 `app.services.writing_agent.tool_policy` 尚不存在。

### Task 2: 抽离策略模块并接入 run_service

**Files:**
- Create: `backend/app/services/writing_agent/tool_policy.py`
- Modify: `backend/app/services/writing_agent/run_service.py`

- [ ] **Step 1: 新增最小策略模块**

```python
REPORT_STOP_TOOLS = frozenset({...})
ALLOWED_REPORT_FOLLOWUPS = frozenset({...})
REPORT_BLOCK_MESSAGES = {...}

def allowed_report_followup(tool_name: str, next_tool_name: str | None) -> bool:
    return (tool_name, next_tool_name) in ALLOWED_REPORT_FOLLOWUPS

def should_stop_after_report(
    tool_name: str,
    output: dict[str, object],
    *,
    step_index: int,
    total_steps: int,
    next_tool_name: str | None = None,
) -> bool:
    ...

def successful_report_block_message(tool_name: str) -> str:
    ...
```

- [ ] **Step 2: 替换 run_service 本地 helper**

`run_service.py` 只从 `tool_policy.py` 引入 `should_stop_after_report` 与 `successful_report_block_message`，删除 `_should_stop_after_report`、`_allowed_report_followup`、`_successful_report_block_message`。

- [ ] **Step 3: 运行 GREEN**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_policy.py -q`
Expected: PASS。

### Task 3: T1 回归验证与报告

**Files:**
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-21-phase97-agent-tool-policy-module.md`

- [ ] **Step 1: 运行相关 run_service 回归**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "blocks_followup_generation or allows_resolution_plan_followup or allows_apply_followup" -q`
Expected: 相关报告阻断和允许后继工具用例全部通过。

- [ ] **Step 2: 静态检查**

Run: `git diff --check`
Expected: 无空白错误。

Run: `Select-String -Path backend\app\services\writing_agent\run_service.py -Pattern 'def _should_stop_after_report|def _allowed_report_followup|def _successful_report_block_message'`
Expected: 无匹配。

- [ ] **Step 3: 写阶段报告、提交并推送**

报告记录计划、实现、RED/GREEN/T1 证据、剩余风险和下一阶段建议。
