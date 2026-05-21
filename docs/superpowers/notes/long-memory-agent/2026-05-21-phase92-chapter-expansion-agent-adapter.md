# Phase92 章节扩写 Agent Adapter 阶段报告

## 阶段目标

将 `expand_chapter_to_target` 从 `WritingAgentRunService._execute_tool()` 的 special-case 分支迁移为 Agent-native 静态工具 adapter，并补上结构化输出契约，让 Agent 可以更稳定地执行“扩写 -> 复审 -> 继续生成/恢复”链路。

## 实际完成

- 新增 `backend/app/services/writing_agent/chapter_expansion_tool.py`
  - 异步封装 `app.core.chapter_expansion.expand_chapter_to_target()`。
  - 保持原扩写、版本写入、trace、retrieval reindex 和阻断逻辑不变。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 新增 async `_expand_chapter_to_target()` handler。
  - 在 `_STATIC_TOOL_ADAPTERS` 注册 `expand_chapter_to_target`。
  - 保留原参数语义：`chapter_index`、`min_word_count`、`extra_instruction`。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_CHAPTER_EXPANSION_OUTPUT`。
  - 将 `expand_chapter_to_target.output_schema` 从通用 `_STATUS_OUTPUT` 收紧为结构化 schema。
  - 在 input schema 中显式暴露 `extra_instruction`。
- 更新 `backend/app/services/writing_agent/run_service.py`
  - 删除 `expand_chapter_to_target` 旧 special-case 分支。
  - 保留 `compress_chapter_to_target` 后续迁移对象。
- 更新测试
  - `backend/tests/test_writing_agent_tool_executor.py`：adapter names、metadata、migration tracking、contract snapshot、async dispatch。
  - `backend/tests/test_writing_agent_tool_registry.py`：直接锁定扩写工具 input/output schema 关键字段。

## 小说进度

本阶段未生成新章节。原因：该阶段继续补齐修订扩写工具链基础设施，服务于后续真实长篇生成中的章节篇幅修复和质量闭环。

## 发现的问题

- `expand_chapter_to_target` 仍留在 `run_service._execute_tool()` special-case 分支中，不符合当前 goal 的统一工具执行方向。
- 扩写工具原输出 schema 仅为 `{status}`，contract snapshot 会报 `output_schema_too_generic`，Agent 难以判断扩写后的版本、字数、trace 和复审建议。
- 扩写工具 input schema 未显式暴露 `extra_instruction`，但旧分支已经支持该参数。

## 已修复的问题

- `expand_chapter_to_target` 已进入 `tool_executor` 静态 adapter。
- `unhandled_internal_writing_agent_tool_names()` 不再将其列为未迁移工具。
- `inspect_agent_tool_contracts` 中该工具不再出现 `missing_agent_native_adapter`。
- `inspect_agent_tool_contracts` 中该工具不再出现 `output_schema_too_generic`。
- API/run_service 入口仍通过统一 executor 执行异步扩写工具，既有扩写、复审、跳过和世界模型阻断回归通过。

## 参考项目吸收

- `hermes-agent`：继续吸收 tools/registry -> unified tool call 的工程模式，减少主 Agent 执行层硬编码。
- `openhuman`：继续参考 controller-only exposure 和 domain/service 分层，把扩写领域逻辑留在 service/core，调度层只保留通用执行。
- `openclaw`：继续参考 runtime tool fixture 的验证思路，用测试锁定工具可见性、参数传递和结果形状。

## 验证记录

验证层级：T1，局部 backend 工具执行、tool registry 和 run_service 回归。

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "expand_chapter_to_target or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：预期失败，4 failed / 1 passed。失败点为 adapter 未注册、metadata 为 `None`、contract snapshot adapter_type 为 `None`、新 wrapper 模块不存在。

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py -k "expand_chapter_to_target or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`5 passed, 49 deselected`。

Run service 回归：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "expand_chapter_to_target" -q
```

结果：`5 passed, 157 deselected`。

Registry schema 直接断言：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_registry.py -k "expand_chapter_has_structured_output_contract" -q
```

结果：`1 passed, 23 deselected`。

T1 组合验证：

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py -k "expand_chapter_to_target or expand_chapter_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`12 passed, 228 deselected`。

质量门：

```powershell
git diff --check
rg -l 'sk-[A-Za-z0-9]{20,}' backend docs --glob '!docs/archive/**'
```

结果：`git diff --check` exit 0；密钥扫描无输出，`rg` exit 1，符合无匹配预期。

## 子代理审查

子代理 `019e49f4-9f70-78a0-9b4a-7d19cef7e137` 完成只读审查：

- 高：`backend/app/services/writing_agent/chapter_expansion_tool.py` 和阶段计划文档是未跟踪文件，提交时必须显式纳入，否则运行时会 `ModuleNotFoundError`。
- 低：executor/contract 测试只验证 gap 消失，没有直接锁定 `_CHAPTER_EXPANSION_OUTPUT` 关键字段。
- 低：output schema 对 blocked/skipped 分支不够严格，但现有 registry 允许非 required 字段和 additionalProperties，本阶段可接受。
- 确认：旧 `run_service` 分支已移除；新 adapter 是异步 handler；业务参数和 core 调用语义未变化。

处理：

- 提交前显式 `git add backend/app/services/writing_agent/chapter_expansion_tool.py` 和 Phase92 文档。
- 已补 `test_agent_tool_registry_expand_chapter_has_structured_output_contract()` 直接锁定关键 schema 字段。
- blocked/skipped schema 严格性记录为后续统一 schema 策略问题，本阶段不扩大范围。

## 未修复但记录的问题

- `compress_chapter_to_target` 仍在 `run_service._execute_tool()` special-case 分支中。
- 扩写工具仍是普通 `write` 工具，缺少显式确认或哈希门禁；本阶段沿用既有行为，后续可统一设计修订类写入工具确认策略。
- output schema 尚未区分 completed/skipped/blocked 的 required 字段集合；后续可设计按状态区分的结果契约。

## 下一阶段建议

Phase93 建议迁移 `compress_chapter_to_target`，完成当前修订工具族从 `run_service` special-case 到 Agent-native adapter 的收束，并同步检查压缩工具的重试结果、retrieval reindex、blocked/skipped schema 和复审推荐链路。
