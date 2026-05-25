# Phase90 修订草稿 Agent Adapter 阶段报告

## 阶段目标

将 `create_revision_draft` 从 `WritingAgentRunService._execute_tool()` 的 special-case 分支迁移为 Agent-native 静态工具 adapter，让“审稿 -> 修订计划 -> 修订草稿”链路继续向统一工具层收敛。

## 实际完成

- 新增 `backend/app/services/writing_agent/revision_draft_tool.py`
  - 封装 `plan_chapter_revision()` 与 `create_revision_draft_from_plan()`。
  - 保持原有修订草稿业务语义不变。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `_create_revision_draft()` handler。
  - 在 `_STATIC_TOOL_ADAPTERS` 注册 `create_revision_draft`。
  - 对外 metadata 暴露为 `category=revision`、`mutability=write`。
- 更新 `backend/app/services/writing_agent/run_service.py`
  - 删除 `create_revision_draft` 旧 special-case 分支。
  - 保留 `apply_planner_revision_patch`、`expand_chapter_to_target`、`compress_chapter_to_target` 后续迁移对象。
- 更新 `backend/tests/test_writing_agent_tool_executor.py`
  - 锁定 static adapter names。
  - 锁定 adapter metadata。
  - 锁定 unhandled migration tracking。
  - 锁定 `inspect_agent_tool_contracts` contract snapshot。
  - 增加 executor dispatch 测试。

## 小说进度

本阶段未生成新章节。原因：本阶段是修订链路工具化基础设施改造，服务于后续真实长篇生成后的自动审稿和修订闭环。

## 发现的问题

- `create_revision_draft` 仍留在 `run_service._execute_tool()` special-case 分支中，不符合当前 goal 的“模块工具化、统一工具契约、统一执行入口”方向。
- contract snapshot 中该工具此前会被识别为缺少 Agent-native adapter。

## 已修复的问题

- `create_revision_draft` 已进入 `tool_executor` 静态 adapter。
- `unhandled_internal_writing_agent_tool_names()` 不再将其列为未迁移工具。
- `inspect_agent_tool_contracts` 中该工具不再出现 `missing_agent_native_adapter` gap。
- API/run_service 入口仍通过统一 executor 执行该工具，既有行为回归通过。

## 参考项目吸收

- `hermes-agent`：继续采用工具 registry / tool discovery 思路，避免把工具执行逻辑散落在主循环中。
- `openhuman`：参考 controller-only exposure 原则，把领域能力暴露到统一 schema/registry/handler，而不是调度层分支。
- `openclaw`：参考 runtime tool fixture 的覆盖方式，用测试确保工具可见性、参数传递和结果形状不漂移。

## 验证记录

验证层级：T1，局部 backend 工具执行与 run_service 回归。

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "create_revision_draft or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：预期失败，4 failed / 1 passed。失败点为 adapter 未注册、metadata 为 `None`、contract snapshot adapter_type 为 `None`、新模块不存在。

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "create_revision_draft or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`5 passed, 45 deselected`。

Run service 回归：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "create_revision_draft" -q
```

结果：`7 passed, 155 deselected`。

T1 组合验证：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "create_revision_draft or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`12 passed, 200 deselected`。

质量门：

```powershell
git diff --check
rg -l 'sk-[A-Za-z0-9]{20,}' backend docs --glob '!docs/archive/**'
```

结果：`git diff --check` exit 0；密钥扫描无输出，`rg` exit 1，符合无匹配预期。

## 子代理审查

尝试两次启动只读子代理审查 Phase90 diff，均因连接中断失败：

- `019e49e5-99f1-73c2-836d-eaecdd797def`
- `019e49e7-6f9e-7170-99ce-aa3212809a70`

本阶段未将子代理作为通过证据，改用本地 diff 审查和验证命令作为结论依据。

## 未修复但记录的问题

- `apply_planner_revision_patch` 仍在 `run_service._execute_tool()` special-case 分支中。
- `expand_chapter_to_target` 仍在 `run_service._execute_tool()` special-case 分支中。
- `compress_chapter_to_target` 仍在 `run_service._execute_tool()` special-case 分支中。
- `create_revision_draft` 仍是普通 `write` 工具，缺少显式确认或哈希门禁；本阶段保持原行为，后续可统一设计修订类写入工具的确认策略。

## 下一阶段建议

Phase91 建议迁移 `apply_planner_revision_patch`，把“修订草稿 -> 应用补丁 -> 复审推荐”继续工具化，并评估是否需要给修订类写入工具补统一确认/哈希门禁。
