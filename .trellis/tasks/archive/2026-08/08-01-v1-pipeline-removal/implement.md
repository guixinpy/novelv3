# P1 v1 生成管线全面绞杀 · 执行计划

> 顺序：迁移（保活）→ 删除（死代码）→ 测试清理。每阶段全量验证。
> 父任务范围：prd.md（需求）+ design.md（方案）+ 本文件（执行）。

## 阶段 1：统一调用路径 + 迁移（保活优先）

### 1.1 Provider.complete
- [ ] base.py 加 `complete()` 默认实现（收集 stream 事件）；DeepSeekProvider 无需覆写
- [ ] test_providers_deepseek.py 补 complete 用例（一次性调用返回 ProviderResponse）

### 1.2 纯函数/数据迁移（prompting 删除前置）
- [ ] `project_chapter_word_range` → `core/chapter_utils.py`；chapter_quality_review/longform_memory 改 import
- [ ] `SetupContextSnapshot`/build_setup_context_values/build_storyline_variables/normalise_json_text
      → `core/setup_context.py`；consistency/background_analyzer/world_context_assembler 改 import
- [ ] `parse_json_safely` → `core/json_utils.py`（deepseek_adapter 删除前先迁出）

### 1.3 迁移三个活跃消费者
- [ ] dialog_utils：`build_provider()` + provider.complete；dialog 模板迁入 dialog_utils
- [ ] l2_extractor：提示词内联 + provider.complete + json_utils
- [ ] chapters.create_or_replace_chapter：章节生成提示词迁入 core 模块 + provider.complete
- [ ] 验证门：`python -m pytest tests/ -q`（dialog/consistency/revisions 相关测试绿）

## 阶段 2：删除死代码

### 2.1 模块删除
- [ ] `core/ai_service.py`、`core/deepseek_adapter.py`、`core/chat_compaction.py`
- [ ] 验证门：`grep -rn "ai_service\|deepseek_adapter\|chat_compaction" backend/app backend/tests` 归零

### 2.2 端点删除
- [ ] outlines.py：generate（344-390 区段）与 expand-window（461-500 区段）——保留 GET/PATCH CRUD
- [ ] setups.py：generate（65-110 区段）——保留 GET
- [ ] storylines.py：generate（99-145 区段）——保留 GET
- [ ] 验证门：`grep -rn "ai_service\|AIService" backend/app/api/outlines.py setups.py storylines.py` 归零

### 2.3 prompting 目录删除
- [ ] `grep -rn "app.prompting" backend/app backend/tests` → 零引用后 `rm -rf backend/app/prompting/`
- [ ] 依赖规则测试：test_dependency_rules 绿

## 阶段 3：测试清理 + 全量验证

### 3.1 测试清理
- [ ] 删除迁移历史测试：test_prompting_generation_migration、test_prompting_contracts、
      test_prompting_chapter_migration（若有）
- [ ] 改造：test_outlines/test_setups/test_storylines 移除 generate 用例（保留 CRUD 用例）；
      test_chapter_revisions/test_l2_extractor/test_config/test_topologies 的 mock 改为 provider
- [ ] 验证门：`cd backend && python -m pytest -q` 全绿（647 基线将因删测试下降，剩余全绿）

### 3.2 全量验证
- [ ] 前端 `vitest run` 485 tests 通过；`vue-tsc --noEmit` 通过
- [ ] `grep -rn "app.prompting\|core.ai_service\|deepseek_adapter\|chat_compaction" backend` 归零
- [ ] 会话回放抽查（200 章 JSONL 加载不依赖 v1）

## 提交计划（独立 commit，按阶段）

1. `harness? no — refactor: v1 迁移 — Provider.complete + 活跃消费者迁移`（阶段 1）
2. `refactor: v1 绞杀 — 删除 ai_service/deepseek_adapter/chat_compaction/生成端点/prompting`（阶段 2）
3. `refactor: v1 绞杀 — 测试清理与基线更新`（阶段 3）

## 回滚点

- 阶段 1 完成即安全提交点（迁移后功能仍全绿，v1 未删）
- 阶段 2 删除端点前确认：无前端/脚本调用（已核实）
- 每阶段 pytest 全绿才进下一阶段

## 验收（父任务 prd 标准）

- [ ] Provider.complete 测试通过；全仓 v1 引用归零
- [ ] athena 聊天/一致性 L2/章节修订/v2 动作测试绿（保活）
- [ ] 后端全量 pytest 绿；前端 vitest + vue-tsc 绿
- [ ] 测试基线更新到 progress-tracker（删除后实测数字）
