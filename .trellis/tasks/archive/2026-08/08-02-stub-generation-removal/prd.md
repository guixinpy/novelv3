# P1 stub 生成端点体系清理（C 方案：删除，前端直连 v2 会话）

## Goal

删除「control-plane 记录」stub 生成体系（4 个生成端点 + 假错误管道 + action 3 个 stub 分支 + 前端 3 个假生成方法），
生成入口收敛为唯一真路径（v2 agent 会话）。四视角评审（创作/产品体验/工程维护/成本收益）一致推荐 C，用户 2026-08-02 拍板执行。

## 背景事实（评审核实）

- `execute_agent_api_tool`（dialog_utils.py:232）stub：硬编码 status="success"，只写 WritingAgentRun 记录
- 4 个生成端点：chapters.generate（无前端调用，死端点）、athena/ontology/generate、athena/evolution/plan/generate（前端 store 有封装但**组件零调用**）
- 假错误管道死分支：`_raise_if_agent_generation_failed`、`LEGACY_GENERATION_400_ERRORS`、`_with_agent_metadata`、错误码映射
- action_execution_service 3 个 stub 动作（generate_setup/storyline/outline）在 app/ 下**无生产调用方**（仅 tests/test_action_execution.py）
- `WritingAgentRun` 后端**无生产读取方**（前端 agent_run_id 来自对话消息 meta，不查表）→ 表可保留空置
- 前端 `project.ts:340` 已示范：generateChapter 已删并注释「use /api/v2/sessions with write_chapter tool」；AgentV2View 会话 UI 已存在
- `generate_chapter` 动作（create_or_replace_chapter 真生成路径）**保留**——它是真实同步生成，被章节修订/v2 动作使用

## Requirements

### R1. 后端删除
- `dialog_utils.py`：删 `execute_agent_api_tool`、`AgentApiToolRunResult`、`_raise_if_agent_generation_failed` 及假错误管道符号（仅 stub 体系使用的）
- `chapters.py`：删 generate 端点（无前端调用死端点）+ 相关 `_raise_if_agent_chapter_generation_failed`/`CHAPTER_GENERATION_ERROR_STATUS_CODES`（若仅被端点用）
- `athena_ontology.py`：删 `generate_ontology` + 常量（ATHENA_ONTOLOGY_*）
- `athena_evolution.py`：删 `generate_evolution_plan` + `_execute_evolution_generate_tool` + 常量（ATHENA_EVOLUTION_*）+ 假错误管道
- `action_execution_service.py`：删 3 个 stub 动作分支（generate_setup/storyline/outline）；动作 label_map 同步清理；`generate_chapter` 保留

### R2. 前端改造
- `client.ts`：删/改 3 个生成方法（generateSetup/generateStoryline/generateOutline）——改注释引导或删除
- `stores/project.ts`：删 3 个对应函数（参照 generateChapter 先例注释「use /api/v2/sessions」）
- 组件层：确认无调用（评审已核实组件零调用——无组件改动）

### R3. 测试清理
- `tests/test_action_execution.py`：删 3 个 stub 动作用例，保留 generate_chapter 与缺项目用例（generate_chapter 测试若存在）
- athena_ontology/athena_evolution 测试中 generate 端点用例删除
- 保留：`WritingAgentRun` 模型与表（空置，审计历史）

## Acceptance Criteria

- [ ] `grep execute_agent_api_tool` 后端归零
- [ ] 4 个生成端点路由删除（前端组件已核实零调用）
- [ ] action 3 个 stub 动作删除后 `action_execution_service` 可 import 且 generate_chapter 正常
- [ ] 前端 vitest 通过（client/store 方法删除后无引用断裂）
- [ ] 后端全量 pytest 通过（595 基线调整）、前端 485 无回归、vue-tsc 通过
- [ ] WritingAgentRun 表保留（模型不删）
- [ ] 独立 commit（message 前缀 `refactor: stub-removal`）

## Out of Scope

- `WritingAgentRun` 表/模型删除（保留，历史审计）
- generate_chapter 真生成路径（保留）
- 前端「引导至 v2 会话」的新交互设计（AgentV2View 已存在，本次只删假方法；引导文案可后续）

## Notes

- 评审成本估算：C ≈ 1.5-2.5 人日（后端 0.5 + 前端 1 + 测试 0.5）
- 删除前 grep 各符号引用确认零残留；每步全量测试
