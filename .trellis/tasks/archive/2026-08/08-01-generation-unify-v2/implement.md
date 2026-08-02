# P1 生成模式统一到 v2 + prompting 全链淘汰 · 执行计划

> 顺序：迁移（保功能）→ 修复（action）→ 删除 → 测试清理。每阶段全量验证。

## 阶段 1：core 模块迁移（保功能）

### 1.1 core/prompt_budget.py
- [ ] `apply_context_budget(blocks, max_chars)` 迁移（原 budgeter.apply 语义：priority 排序、
      omitted/truncated 跟踪、truncated marker）
- [ ] 测试：超长块截断 + priority 保序 + 空预算（新 `test_prompt_budget.py`）

### 1.2 core/chapter_generation.py
- [ ] 迁入 variables/context_blocks/trace_blocks/max_tokens 函数与常量（原 providers/chapter.py 活跃部分）
- [ ] 渲染：直接读 `backend/prompts/generate_chapter.txt` + str.format（对齐原 renderer 语义）
- [ ] 预算：接入 apply_context_budget
- [ ] `api/chapters._build_chapter_call_payload` 改调；prompt_assembler 引用移除
- [ ] 验证门：test_chapter_revisions 全绿（mock 仍是 build_provider，断言更新提示词片段）

### 1.3 core/dialog_prompts.py
- [ ] dialog.py 全量迁移（athena/hermes 分支 + 上下文块 + 历史消息）
- [ ] 渲染改直接读模板 + format；prompt_id→template_name 映射与 required_vars 校验内联
- [ ] dialog_utils 改 import
- [ ] 验证门：test_athena_dialog / dialog 相关测试全绿

## 阶段 2：action_execution_service 修复（阶段 2 遗漏）

- [ ] generate_setup → athena_ontology 生成逻辑（stub 记录）
- [ ] generate_storyline/generate_outline → athena_evolution._execute_evolution_generate_tool
- [ ] 新增测试：3 动作执行成功 + 写运行记录
- [ ] 验证门：`python -m pytest tests/ -q` 全绿

## 阶段 3：删除

- [ ] `rm -rf app/prompting/`；`grep -rn "app.prompting" app/ tests/` 归零
- [ ] 删 6 个死亡模板（generate_outline/generate_setup/generate_storyline/athena_extract_l2/athena_world_model_semantic_check）
- [ ] 删 test_prompting_contracts / test_prompting_chapter_migration
- [ ] 验证门：全量 pytest + 依赖规则测试

## 阶段 4：全量验证 + 收尾

- [ ] 后端全量 pytest 绿（620 基线调整后）
- [ ] 前端 vitest + vue-tsc 绿
- [ ] 会话回放 20 JSONL 成功
- [ ] progress-tracker 记录（prompting 全链淘汰 + 生成统一 v2 风格 + execute_agent_api_tool stub 待决策）
- [ ] 独立 commit ×4（阶段 1-4）

## 回滚点

- 阶段 1 完成即安全点（功能全绿、prompting 未删）
- 阶段 3 删除前：grep 归零断言 + 全量测试绿
- 每阶段独立 commit，失败回滚上一 commit
