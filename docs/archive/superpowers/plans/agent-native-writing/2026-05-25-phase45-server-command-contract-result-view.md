# Phase45: Server Command Contract Result View

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让服务端历史消息重建的 `action_result_view.detail_items` 也能展示 `agent_command_contracts` 摘要。

**Architecture:** 复用 `backend/app/services/actions/action_result_view.py` 中已有 `_agent_discovery_detail_items(...)` 汇总入口，在 Agent 身份、工具面、策略审计之后追加命令契约 bounded summary。只展示计数，不展示完整命令列表或 trace source。

**Tech Stack:** FastAPI service helper、pytest。

---

## 参考项目吸收

- hermes-agent：历史运行/消息回放必须保留运行控制面的诊断摘要，否则实时卡片与历史卡片会产生观测断层。
- openhuman：消息回放展示 bounded recall summary，不暴露内部 provenance path。

## 成功标准

1. `DialogMessageService.list_messages(...)` 重建历史消息时，`action_result_view.detail_items` 包含：
   - `命令契约: 已投影`
   - `控制命令: N 个`
   - `契约缺口: N 个`
2. `detail_items` 不包含 `planner_trace.agent_health_projection.command_contracts` 或完整 `commands` 列表。
3. 不影响现有 recovery preview、recommended followup、Agent profile policy audit 展示。

## Task 1: Backend Result View Projection

**Files:**
- Modify: `backend/app/services/actions/action_result_view.py`
- Test: `backend/tests/test_dialogs.py`

- [ ] **Step 1: Write failing test**

Add a test after `test_get_messages_includes_agent_profile_policy_audit_detail_item`:

```python
def test_get_messages_includes_agent_command_contract_detail_items(db_session):
    project = Project(name="Agent Command Contract Result View")
    db_session.add(project)
    db_session.commit()
    dialog = dialogs_api._get_or_create_dialog(db_session, project.id)
    dialogs_api._save_message(
        db_session,
        dialog.id,
        "assistant",
        "Agent 已检查命令契约。",
        action_result={
            "type": "plan_recovery_tools",
            "status": "success",
            "data": {
                "agent_profile": "orchestrator",
                "agent_command_contracts": {
                    "source": "planner_trace.agent_health_projection.command_contracts",
                    "summary": {
                        "agent_control_commands": 2,
                        "gap_count": 0,
                    },
                    "commands": [{"name": "continue"}],
                },
            },
        },
    )

    messages = DialogMessageService(db_session).list_messages(project.id)
    detail_items = messages[-1]["action_result_view"]["detail_items"]

    assert {"label": "Agent 身份", "value": "编排主控"} in detail_items
    assert {"label": "命令契约", "value": "已投影"} in detail_items
    assert {"label": "控制命令", "value": "2 个"} in detail_items
    assert {"label": "契约缺口", "value": "0 个"} in detail_items
    assert "planner_trace.agent_health_projection.command_contracts" not in str(detail_items)
    assert "continue" not in str(detail_items)
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_command_contract_detail_items" -q
```

Expected: FAIL because command contract detail items are absent.

- [ ] **Step 3: Implement minimal helper**

Add helper:

```python
def _agent_command_contract_detail_items(data: dict) -> list[dict[str, str]]:
    contracts = data.get("agent_command_contracts") if isinstance(data.get("agent_command_contracts"), dict) else {}
    summary = contracts.get("summary") if isinstance(contracts.get("summary"), dict) else {}
    if not summary:
        return []
    items = [{"label": "命令契约", "value": "已投影"}]
    control_commands = _optional_int(summary.get("agent_control_commands"))
    if control_commands is not None:
        items.append({"label": "控制命令", "value": f"{control_commands} 个"})
    gap_count = _optional_int(summary.get("gap_count"))
    if gap_count is not None:
        items.append({"label": "契约缺口", "value": f"{gap_count} 个"})
    return items
```

Append it inside `_agent_discovery_detail_items(...)` after policy audit.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_command_contract_detail_items" -q
```

Expected: PASS.

## Task 2: Phase Verification and Report

**Files:**
- Create: `docs/superpowers/notes/agent-native-writing/2026-05-25-phase45-server-command-contract-result-view.md`

- [ ] **Step 1: Run targeted verification**

Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_command_contract_detail_items or agent_profile_policy_audit_detail_item or action_result_view_for_recovery_preview or action_result_view_for_recommended_followup_result_view" -q
git diff --check
```

- [ ] **Step 2: Write phase report**

Record RED evidence, GREEN evidence, changed files, and next-phase recommendation.
