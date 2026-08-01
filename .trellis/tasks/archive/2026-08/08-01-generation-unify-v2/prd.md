# P1 生成模式统一到 v2 + prompting 全链淘汰

## Goal

彻底消除 v1 遗留的提示词子系统（`app/prompting/` + `backend/prompts/`），
所有一次性生成（章节修订、athena 聊天、v2 动作执行）统一为「内联提示词 + `provider.complete`」
的 v2 风格；修复 v1 绞杀阶段 2 遗漏的 action_execution_service 死引用。
执行形态说明：agent 会话（v2_sessions）是异步 SSE 接口，同步 API（修订再生成/动作执行）
无法直接驱动会话，故「统一到 v2」= 提示词构造统一为 v2 风格的一次性调用（与 l2_extractor 一致），
不再存在独立提示词子系统包。

## 背景事实（2026-08-01 调研确认）

- `app/prompting/` 由 2 个活跃消费者依赖：`chapters._build_chapter_call_payload`（修订再生成/v2 动作）、
  `dialog_utils._free_chat_reply`（athena 聊天）
- 装配链：`assembler` → `registry`（模板注册）+ `renderer`（backend/prompts/*.txt 渲染）+ `budgeter`（上下文预算截断）+ `tracing`
- **阶段 2 遗漏**：`action_execution_service` 的 generate_setup/generate_storyline/generate_outline 3 个动作
  仍惰性 import 已删函数（运行时 ImportError），无测试覆盖
- `execute_agent_api_tool`（dialog_utils）是 stub：只写 WritingAgentRun 记录不真生成；
  `chapters.generate` 端点（走它）实际不生成内容——该端点无前端调用，是死端点（不纳入本次，单独标记）

## Requirements

### R1. 修复 action_execution_service（阶段 2 遗漏）
- generate_setup/generate_storyline/generate_outline 3 动作 → 改调 athena 生成服务
  （`core/athena_ontology`/`core/athena_longform` 的对应生成函数，前端已走 athena 路径）
- generate_chapter → 走 `chapters.create_or_replace_chapter`（保留，见 R2）
- 补动作执行测试（现有无覆盖）

### R2. 章节生成提示词内联（保留预算截断功能）
- `_build_chapter_call_payload` 的 PromptAssembler + registry + renderer 替换为：
  - `generate_chapter.txt` 模板 → 内联为 `core/chapter_generation.py` 的提示词常量（str.format 渲染，同 l2 风格）
  - **上下文预算截断**（budgeter 的 max_context_chars 逻辑）→ 迁移为 core 纯函数（`truncate_context_blocks`），
    行为不变（超长 Setup 截断是 200 章实验的上下文管理关键）
  - `build_chapter_prompt_variables`/`build_chapter_prompt_context_blocks`（在 chapter.py 模板文件）→ 迁入 core/chapter_generation.py
- `create_or_replace_chapter` 保留（同步 API 语义），LLM 调用已是 provider.complete ✓

### R3. dialog 提示词迁移
- `prompting/providers/dialog.py`（624 行，athena/hermes 分支 + 上下文块构建）→ 整体迁移为 `core/dialog_prompts.py`
  （模板渲染从 registry 改为直接读 `backend/prompts/*.txt` 或内联常量；budget 逻辑同上 R2）
- `_free_chat_reply` 保持 provider.complete ✓，仅 import 路径变化

### R4. prompting 全链删除
- `app/prompting/`（assembler/registry/renderer/budgeter/contracts/tracing/command_args/errors/providers/全部）删除
- `backend/prompts/*.txt`：被迁移使用的模板（generate_chapter/chat_hermes/chat_athena/compact_dialog_context/
  diagnose_project 等）迁至 `core/` 对应模块内联或保留文件由 core 读取；其余（generate_outline/setup/storyline/
  athena_extract_l2 等）随引用方淘汰删除
- 依赖规则测试保持通过

### R5. 测试清理
- 删除：test_prompting_contracts（测 registry/渲染/预算——全淘汰）、test_prompting_chapter_migration（测章节模板迁移）
- 改造：test_chapter_revisions（mock build_provider 不变，断言提示词内容变化处更新）、
  test_athena_dialog 等（dialog import 路径变化）
- 新增：action_execution_service 的 3 个 generate 动作测试

## Acceptance Criteria

- [ ] action_execution_service 全动作可执行（generate_setup/storyline/outline 不再 ImportError）
- [ ] `app/prompting/` 与 `backend/prompts/` 全部删除；`grep app.prompting` 归零
- [ ] 章节修订再生成：功能与测试通过（提示词内联后 mock build_provider 不变）
- [ ] athena 聊天：功能与测试通过（import 路径变化）
- [ ] 上下文预算截断行为不变（core 纯函数测试覆盖：超长 Setup 截断标记）
- [ ] 后端全量 pytest 通过（620 基线调整）、前端 vitest + vue-tsc 通过
- [ ] 会话回放 20 个 JSONL 加载成功
- [ ] 独立 commit：R1 修复 → R2/R3 迁移 → R4 删除 → R5 测试清理

## Notes

- 迁移先于删除（保功能优先）；budgeter 截断逻辑不得丢失。
- `execute_agent_api_tool` stub 与 `chapters.generate` 死端点：不在本次范围，progress-tracker 记录待决策。
