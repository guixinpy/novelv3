# Phase12 Report: Memory Route Degraded Retrieval Coverage

## 本阶段目标

把 `inspect_agent_memory_route` 在“长篇记忆存在、维护 ready、检索索引为空”时的状态从隐式诊断提升为 Agent 可消费的 provenance recovery。

## 实现内容

- `memory_provenance.status` 保持 `degraded`，用于区别于 `blocked` 和 `available`。
- `memory_provenance.recovery.status` 在退化检索覆盖下返回 `optional`。
- `memory_provenance.recovery.tools` 提供只读的 `inspect_agent_memory_route` 复查请求。
- `memory_provenance.recovery.write_tools` 单独列出 `repair_longform_maintenance`，并标记 `write_policy: requires_confirmation`。

## 设计取舍

- 采用 openhuman 式的来源/覆盖边界表达：Agent 能看见长篇记忆、维护诊断、检索索引分别来自哪里。
- 采用 openclaw 式的 fallback 思路：退化状态不阻断写作，但明确下一步诊断与修复路径。
- 不把检索索引缺失升级成 blocked，因为已有长篇记忆时系统仍可继续写，只是召回质量下降。

## 验证

- RED: `pytest tests/test_writing_agent_memory_route.py -k degraded -q`
  - 初始失败：`provenance["recovery"]["status"]` 为 `none`，期望 `optional`。
- GREEN: `pytest tests/test_writing_agent_memory_route.py -k degraded -q`
  - 结果：`1 passed, 2 deselected`
- T1: `pytest tests/test_writing_agent_memory_route.py tests/test_writing_agent_tool_executor.py -k "memory_route or inspect_agent_memory_route" -q`
  - 结果：`5 passed, 153 deselected`

## 后续建议

下一阶段应收紧 recommendation normalizer 的来源字段和读写分离表达：当前 `tool_recommendations` 从 `memory_provenance.recovery.tools` 读取可执行只读工具，但 `source_fields` 仍记为 `memory_provenance.recovery.next_tools`，容易让审计方误以为写工具也会进入自动 follow-up。
