# T1 内核健壮性：hook 兜底 + 通用错误恢复 + 压缩重放测试

> 父任务：08-01-harness-optimization（design.md D6 决策）。来源：harness-engineering-list §一.1 + §二.1。

## Goal

让 loop/harness 层在任何钩子异常、工具错误、压缩重放场景下不崩不炸，并给模型恢复指引。

## Requirements

### R1. before_tool_call 钩子自身异常兜底（loop.py `_execute_one`）
- 现状：`before_tool_call`（审批门回调）抛出异常会击穿整个 run_turn（loop.py:181-191 无保护）。
- 要求：钩子抛异常 → **fail-closed 拦截**该工具调用（返回错误信息给模型，说明前置检查异常，
  请重试或换工具），回合不崩；emit 事件照常发出（记 is_error）。

### R2. 回合内工具错误 → 通用「错误诊断 + 下一步建议」注入（harness.py）
- 现状：仅 GuardTripped 后注入恢复建议（harness.py:250-258）；普通工具错误只回填给模型，无主动引导。
- 要求：`run_turn` 返回后，harness 检查本回合工具结果，存在 is_error 时注入一条 user 消息：
  「本回合 N 次工具调用失败（tool1: 原因摘要; tool2: …）。建议：…」。
- 防抖：每回合最多注入 1 条；错误恢复注入与 GuardTripped 注入互斥（guard 版优先级更高，已有）。
- 实现位置：`_run_one_turn` 内 `last_guard_diagnosis` 模式扩展为「工具错误汇总」；
  需要 loop 暴露工具错误信息 → 通过 `ToolCallFinished` 事件（is_error=True）收集。

### R3. 压缩后重放一致性测试矩阵
- 现有 `_sanitize_tool_message_order`（harness.py:29-50）已实现孤立 tool 消息清洗；
  补完整测试矩阵覆盖边界：tool 消息开头 / 连续 tool / assistant 无 tool_calls 后有 tool /
  多轮压缩嵌套 / sanitize 后 load 重放（_load 与 compaction 快照路径）。
- 现有 `test_compaction.py`、`test_harness.py` 扩展，新增 ≥5 个用例。

## Acceptance Criteria

- [ ] before_tool_call 抛异常 → run_turn 不抛错、回合正常结束、模型收到 fail-closed 错误信息
- [ ] 回合内工具错误 → 下一轮自动注入「错误诊断 + 下一步建议」（每回合 ≤1 条）
- [ ] 压缩重放矩阵测试通过（新增 ≥5 个边界用例）
- [ ] 后端全量 pytest 通过（基线 596 passed，只增不减）
- [ ] 前端 vitest 无回归（485 tests）
- [ ] 独立 commit（message 前缀 `harness: T1`）

## 实现要点（已核实代码位置）

- `backend/app/agent/loop.py:181-191` — `_execute_one` before_tool_call 调用处，加 try/except
- `backend/app/agent/harness.py:217-258` — persisting_sink 收集 ToolCallFinished 错误 + 回合末注入
- `backend/app/agent/harness.py:29-50` — `_sanitize_tool_message_order`（测试对象）
- 测试文件：`backend/tests/agent/test_loop.py`、`test_harness.py`、`test_compaction.py`

## Notes

- 不改变事件契约；`ToolCallFinished` 已有 is_error 字段，无需新事件。
- R2 的注入文本仿照现有 guard 版措辞风格（harness.py:254-258）。
