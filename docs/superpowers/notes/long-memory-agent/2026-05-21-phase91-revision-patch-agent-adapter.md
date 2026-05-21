# Phase91 修订补丁 Agent Adapter 阶段报告

## 阶段目标

将 `apply_planner_revision_patch` 从 `WritingAgentRunService._execute_tool()` 的 special-case 分支迁移为 Agent-native 静态工具 adapter，并补上结构化输出契约，让 Agent 可以更稳定地执行“修订草稿 -> 应用补丁 -> 复审”链路。

## 实际完成

- 新增 `backend/app/services/writing_agent/revision_patch_tool.py`
  - 封装 `app.core.chapter_revision_apply.apply_planner_revision_patch()`。
  - 保持原有章节补丁应用、版本写入、revision 状态更新逻辑不变。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 新增 `_apply_planner_revision_patch()` handler。
  - 在 `_STATIC_TOOL_ADAPTERS` 注册 `apply_planner_revision_patch`。
  - 保留 `revision_id.strip() or None` 参数清洗行为。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_REVISION_PATCH_OUTPUT`。
  - 将 `apply_planner_revision_patch.output_schema` 从通用 `_STATUS_OUTPUT` 收紧为结构化 schema。
- 更新 `backend/app/services/writing_agent/run_service.py`
  - 删除 `apply_planner_revision_patch` 旧 special-case 分支。
  - 保留 `expand_chapter_to_target`、`compress_chapter_to_target` 后续迁移对象。
- 更新 `backend/tests/test_writing_agent_tool_executor.py`
  - 锁定 static adapter names。
  - 锁定 adapter metadata。
  - 锁定 unhandled migration tracking。
  - 锁定 `inspect_agent_tool_contracts` 中 adapter 和 output schema gap。
  - 增加 executor dispatch 测试，覆盖 `chapter_index` 转换和 `revision_id` trim。

## 小说进度

本阶段未生成新章节。原因：该阶段继续补齐修订工具链基础设施，服务于后续真实长篇生成后的自动修订闭环。

## 发现的问题

- `apply_planner_revision_patch` 仍留在 `run_service._execute_tool()` special-case 分支中，不符合“模块工具化、统一工具执行入口”的方向。
- 该工具原输出 schema 仅为 `{status}`，contract snapshot 会报 `output_schema_too_generic`，Agent 难以判断补丁是否实际应用、版本是否写入、下一步是否复审。
- contract 层会按 `apply_` 前缀将其归类为 `guarded_write`，而 adapter metadata 仍记录实际执行 adapter 的 `write`；测试中需要区分这两个层级。

## 已修复的问题

- `apply_planner_revision_patch` 已进入 `tool_executor` 静态 adapter。
- `unhandled_internal_writing_agent_tool_names()` 不再将其列为未迁移工具。
- `inspect_agent_tool_contracts` 中该工具不再出现 `missing_agent_native_adapter`。
- `inspect_agent_tool_contracts` 中该工具不再出现 `output_schema_too_generic`。
- API/run_service 入口仍通过统一 executor 执行该工具，既有章节内容和版本写入回归通过。

## 参考项目吸收

- `hermes-agent`：继续吸收工具 registry / tool discovery 思路，避免把工具执行逻辑散落在 Agent 主循环里。
- `openhuman`：继续参考 controller-only exposure 原则，把领域能力迁入统一 schema/registry/handler，而不是调度层分支。
- `openclaw`：继续参考 runtime tool fixture 思路，用测试锁定工具可见性、参数传递和结果形状。

## 验证记录

验证层级：T1，局部 backend 工具执行与 run_service 回归。

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_planner_revision_patch or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：预期失败，4 failed / 1 passed。失败点为 adapter 未注册、metadata 为 `None`、contract snapshot adapter_type 为 `None`、新模块不存在。

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "apply_planner_revision_patch or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`5 passed, 47 deselected`。

Run service 回归：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "apply_planner_revision_patch" -q
```

结果：`2 passed, 160 deselected`。

T1 组合验证：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_runs.py -k "apply_planner_revision_patch or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`7 passed, 207 deselected`。

质量门：

```powershell
git diff --check
rg -l 'sk-[A-Za-z0-9]{20,}' backend docs --glob '!docs/archive/**'
```

结果：`git diff --check` exit 0；密钥扫描无输出，`rg` exit 1，符合无匹配预期。

## 子代理审查

子代理 `019e49ee-4dc5-7631-b92e-17a7cbfb6e28` 完成只读审查：

- P1：`backend/app/services/writing_agent/revision_patch_tool.py` 是新文件，提交前必须显式纳入 `git add`，否则运行时会 `ImportError`。
- 未发现业务语义改变。
- metadata `write` 与 contract `guarded_write` 的区分合理，和现有 `apply_world_model_proposal_resolution` 模式一致。
- 未发现明显测试遗漏。

处理：P1 属于提交流程风险，最终提交时必须显式 `git add backend/app/services/writing_agent/revision_patch_tool.py`。

## 未修复但记录的问题

- `expand_chapter_to_target` 仍在 `run_service._execute_tool()` special-case 分支中。
- `compress_chapter_to_target` 仍在 `run_service._execute_tool()` special-case 分支中。
- `apply_planner_revision_patch` contract 已是 `guarded_write`，但目前沿用既有运行行为，未新增显式确认参数或哈希门禁；后续可统一设计修订类写入工具确认策略。

## 下一阶段建议

Phase92 建议迁移 `expand_chapter_to_target`，把修订链路中的扩写工具也迁到 Agent-native adapter，并检查扩写后对 longform memory、retrieval 和 review 的推荐链路是否足够结构化。
