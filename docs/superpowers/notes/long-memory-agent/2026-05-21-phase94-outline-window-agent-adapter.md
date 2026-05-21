# Phase94 Report: Outline Window Agent Adapter

## Summary

本阶段将 `expand_outline_window` 从 `WritingAgentRunService` special-case 分支迁移为 Agent-native 静态 adapter，并为大纲窗口扩展工具补齐结构化输出契约。

## Changes

- 新增 `backend/app/services/writing_agent/outline_window_tool.py`
  - 聚焦包装 `app.api.outlines.expand_outline_window()`。
  - 汇总 Outline 对象上的 `outline_expansion_result`、`last_expansion_trace_id` 和基础字段为 Agent 工具输出。
  - 使用 `from app.api import outlines as outline_api` 后再调用函数，保留现有 `app.api.outlines.expand_outline_window` monkeypatch 路径。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 新增 async `_expand_outline_window()`。
  - 注册 `expand_outline_window` 静态 adapter。
  - 保持旧分支参数等价：`start_chapter -> chapter_index -> 1`、`end_chapter -> start_chapter`、`params.command_args -> tool.command_args -> None`。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_OUTLINE_WINDOW_OUTPUT`。
  - 将 `expand_outline_window.output_schema` 从 `_STATUS_OUTPUT` 改为结构化 schema。
- 更新 `backend/app/services/writing_agent/run_service.py`
  - 删除 `expand_outline_window` 直接执行分支。
  - 保留 `import_setup_world_model` 和 `seed_continuity_anchor_proposals` legacy 分支。
- 更新测试
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_tool_registry.py`

## Reference Absorption

- `hermes-agent`：沿用工具 registry + 统一 tool-call 入口方向，减少 Agent 主运行服务中对具体工具的硬编码。
- `openhuman`：当前阶段只把 dispatch 与工具行为隔离；后续可以继续把 `app.api.outlines` 中的业务逻辑下沉到领域 service。
- `openclaw`：用 runtime tool fixture 的方式锁定工具可见性、参数透传和结果形状。

## Validation

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "expand_outline_window or expand_outline_window_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：预期失败，暴露缺 adapter、缺 wrapper、缺结构化 schema。

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "expand_outline_window or expand_outline_window_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`7 passed, 77 deselected`

Run service focused regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "expand_outline_window or recovery_execute" -q
```

结果：`3 passed, 159 deselected`

Outline API regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_outlines.py -k "expand_outline_window" -q
```

结果：`3 passed, 13 deselected`

T1 combined:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py backend/tests/test_outlines.py -k "expand_outline_window or expand_outline_window_has_structured_output_contract or recovery_execute or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`13 passed, 249 deselected`

Static checks:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

结果：`git diff --check` 无输出；secret scan 无匹配。

## Subagent Review

只读审查员结论：

- 旧 `WritingAgentRunService` 直接执行 `expand_outline_window` 分支已移除。
- 新 adapter 参数解析与旧分支等价。
- `outline_window_tool.py` 保留现有 API 行为，并不会破坏 `app.api.outlines.expand_outline_window` monkeypatch 测试。
- registry schema 足以避开当前 contract snapshot 的 `output_schema_too_generic`。
- 测试覆盖 adapter names、metadata、contract snapshot、dispatch、registry schema，以及既有 run_service/API 回归。
- 唯一风险是新 adapter 文件、阶段计划和本报告必须显式纳入提交。

处理：提交前显式 stage `outline_window_tool.py`、Phase94 计划文档和本报告。

## Novel Progress

本阶段未生成新章节。原因：本阶段属于 Agent 工具化基础设施阶段，直接提升“缺章节大纲时 Agent 自主恢复并继续创作”的能力。

## Residual Risks

- `expand_outline_window` 仍复用 `app.api.outlines.expand_outline_window()`，业务逻辑还没有完全从 API 层下沉到领域 service。当前迁移解决了 Agent dispatch 硬编码问题，后续仍可继续拆分 API 内部实现。
- `run_service` 中仍有 legacy internal branches：`import_setup_world_model`、`seed_continuity_anchor_proposals`。
- 写入类工具的 confirm/hash 门禁仍需统一策略，避免 Agent 未来在批量自动执行中误写。

## Next Recommendation

下一阶段建议处理 `import_setup_world_model` 或 `seed_continuity_anchor_proposals`。如果继续沿着“从低细节用户输入到可写章节”的关键路径推进，优先迁移 `import_setup_world_model`，让项目初始化后的世界模型导入也进入统一 Agent-native 工具层。
