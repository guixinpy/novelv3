# Phase93 Report: Chapter Compression Agent Adapter

## Summary

本阶段将 `compress_chapter_to_target` 从 `WritingAgentRunService` special-case 分支迁移为 Agent-native 静态 adapter，并为压缩工具补齐结构化输入/输出契约。

## Changes

- 新增 `backend/app/services/writing_agent/chapter_compression_tool.py`
  - 聚焦包装 `app.core.chapter_compression.compress_chapter_to_target()`。
  - 保持原压缩、禁用词重试、世界模型阻断、版本写入、Trace 和索引刷新逻辑不变。
- 更新 `backend/app/services/writing_agent/tool_executor.py`
  - 新增 async `_compress_chapter_to_target()`。
  - 注册 `compress_chapter_to_target` 静态 adapter。
  - 继续保持旧分支参数等价：`chapter_index`、`target_max_word_count`、`extra_instruction`、trim/filter 后的 `forbidden_terms`。
- 更新 `backend/app/services/writing_agent/tool_registry.py`
  - 新增 `_CHAPTER_COMPRESSION_OUTPUT`。
  - `compress_chapter_to_target` input schema 显式暴露 `extra_instruction` 和 `forbidden_terms`。
  - output schema 覆盖状态、字数、版本、Trace、禁用词、重试、确定性修复/裁剪、warnings、world-model 阻断和 next tools。
- 更新 `backend/app/services/writing_agent/run_service.py`
  - 删除 `compress_chapter_to_target` 直接执行分支。
  - 保留后置 report/follow-up guard 文案。
- 更新测试
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_tool_registry.py`

## Reference Absorption

- `hermes-agent`：延续“工具注册 + 统一 tool-call 入口”的工程方向，减少主运行服务硬编码分支。
- `openhuman`：领域行为保留在 core/service，dispatch 层只负责参数解析与转发。
- `openclaw`：用 runtime tool fixture 思路锁定工具可见性、参数传递和结果形状，避免工具迁移后发生调用漂移。

## Validation

RED:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "compress_chapter_to_target or compress_chapter_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：预期失败，暴露缺 adapter、缺 wrapper、缺结构化 schema。

GREEN:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py -k "compress_chapter_to_target or compress_chapter_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`7 passed, 74 deselected`

Run service regression:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "compress_chapter_to_target" -q
```

结果：`14 passed, 148 deselected`

T1 combined:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_runs.py -k "compress_chapter_to_target or compress_chapter_has_structured_output_contract or unhandled_internal_tools or inspect_agent_tool_contracts" -q
```

结果：`21 passed, 222 deselected`

Static checks:

```powershell
git diff --check
rg -l "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

结果：`git diff --check` 无输出；secret scan 无匹配。

## Subagent Review

只读审查员结论：

- 未发现旧 `run_service` 直接执行压缩分支残留。
- 参数等价性成立。
- schema 足以避开当前 contract snapshot 的 `output_schema_too_generic`。
- 测试覆盖方向完整。
- 唯一高风险点是新 adapter 文件和阶段计划文件处于未跟踪状态，提交时必须显式纳入。

处理：提交前显式 stage `chapter_compression_tool.py`、Phase93 计划文档和本报告。

## Novel Progress

本阶段未生成新章节。原因：本阶段属于 Agent 工具化基础设施阶段，直接提升后续长篇生成过程中章节篇幅失控后的自动修订能力。

## Residual Risks

- `compress_chapter_to_target` 仍是普通 write 工具，后续需要统一讨论写入类修订工具是否要补 confirm/hash 门禁。
- `run_service` 中仍有少量 legacy internal branches：`import_setup_world_model`、`expand_outline_window`、`seed_continuity_anchor_proposals`。它们是后续迁移候选。

## Next Recommendation

下一阶段建议优先处理 `expand_outline_window`，因为它位于“低细节用户输入 -> Agent 自主补大纲窗口 -> 再生成章节”的关键路径，直接关系到用户不提供详细章节剧情时的长篇自主推进能力。
