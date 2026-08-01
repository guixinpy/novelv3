# P1 v1 生成管线全面绞杀

## Goal

统一 LLM 调用路径到 v2 provider（`app/agent/providers/`），删除 v1 旧生成管线
（`ai_service` + `deepseek_adapter` + 双套 HTTP 客户端 + 死亡提示词模板），
保留活跃功能（athena 聊天、一致性 L2、章节修订、v2 动作执行）并迁移其 LLM 调用。
2026-08-01 决策：选项 C（全面绞杀），用户拍板。

## 依赖图（2026-08-01 代码级核实）

```
ai_service.complete 调用点（7 处）：
  - api/chapters.py:433  ← create_or_replace_chapter（被 chapter_revisions 修订再生成、
    action_execution_service v2 动作执行使用 → 活跃，需迁移）
  - api/dialog_utils.py:202 ← athena 自由聊天（活跃，需迁移）
  - api/outlines.py:344,461 ← generate/expand-window 端点（无前端调用 → 死，删除）
  - api/setups.py:65        ← generate 端点（死，删除）
  - api/storylines.py:99    ← generate 端点（死，删除）
  - core/chat_compaction.py:75 ← v1 对话压缩（无调用方 → 死模块，删除）

prompting/ 引用分类：
  - 活跃纯函数/数据：SetupContextSnapshot + build_setup_context_values/build_storyline_variables
    （consistency/background_analyzer/world_context_assembler 用）、normalise_json_text
    （world_context_assembler 用）、project_chapter_word_range（chapter_quality_review/longform_memory 用）
  - 活跃模板：dialog.py（dialog_utils 用，624 行）
  - 死亡模板（随生成端点删）：chapter/outline/setup/storyline 生成链 + knowledge_base/
    few_shot/style/longform/retrieval/project
  - athena 核心文件不直接引用 prompting（仅 dialog_utils 间接）
```

## Requirements

### R1. 统一 LLM 调用路径
- `app/agent/providers/base.py` 增加 `complete(messages, tools=None, **kwargs) -> ProviderResponse`
  便捷方法（非流式一次性调用）；`DeepSeekProvider` 实现为 stream() 的收集封装。
- 所有内部 LLM 调用（dialog_utils、l2_extractor、create_or_replace_chapter）改走 `provider.complete`。

### R2. 删除（死代码）
- `core/ai_service.py`、`core/deepseek_adapter.py`（只被 ai_service 用）
- `core/chat_compaction.py`（无调用方）
- 生成端点：`outlines.py` generate/expand-window、`setups.py` generate、`storylines.py` generate
- prompting 死亡模板：chapter/outline/setup/storyline 生成链 + knowledge_base/few_shot/style/
  longform/retrieval/project（随端点删除后无引用者）
- 相关测试：test_outlines/test_setups/test_storylines 的 generate 用例、test_prompting_generation_migration 等

### R3. 迁移（活跃功能保活）
- `dialog_utils._free_chat_reply`：ai_service.complete → provider.complete；dialog 模板迁入 dialog_utils
- `l2_extractor`：PromptAssembler + ai_service → 提示词内联 + provider.complete（consistency L2 保活）
- `chapters.create_or_replace_chapter`：ai_service.complete → provider.complete；
  章节生成提示词链迁移到 chapters.py 内部或 core 模块（chapter_revisions、action_execution_service 保活）
- 纯函数/数据迁移：`project_chapter_word_range` → `core/chapter_utils.py`；
  SetupContextSnapshot + build_* + normalise_json_text → `core/setup_context.py`（或随引用模块内联）

### R4. 保留
- chapters.py 的 generate 端点（已走 v2 agent tool，不动）
- CRUD API（前端读取基础数据依赖）

## Acceptance Criteria

- [ ] `Provider.complete()` 存在且 DeepSeekProvider 实现；provider 测试通过
- [ ] 全仓 `ai_service` / `deepseek_adapter` / `chat_compaction` 引用归零
- [ ] 删除的 4 个生成端点无残留路由；前端无调用（已核实零调用）
- [ ] athena 聊天、consistency L2 deep check、章节修订、v2 动作执行路径的测试全部通过（保活验证）
- [ ] 后端全量 pytest 通过（647 基线，删除相关测试后应大幅下降但剩余全绿）
- [ ] 前端 vitest 通过 + vue-tsc 通过
- [ ] 依赖规则测试（test_dependency_rules）通过
- [ ] 独立 commit，按「迁移 → 删除 → 清理测试」三步提交

## Notes

- 迁移先于删除（保活优先）：先让活跃功能走 provider.complete，再删死代码。
- prompting 目录最终可整体删除（活跃内容全部迁出后）。
- 不新增第三方依赖（httpx 已有）。
